import httpx
import structlog
import asyncio
import re

from app.core.config import settings
from app.core.exceptions import UnauthorizedException

logger = structlog.get_logger()

class GraphService:
    """Microsoft Graph API를 통해 Entra ID 리소스를 관리하는 서비스"""

    def __init__(self):
        self.base_url = "https://graph.microsoft.com/v1.0"

    async def assign_user_to_app(self, tenant_id: str, user_identifier: str) -> bool:
        """특정 사용자를 Enterprise Application(Service Principal)에 할당합니다."""
        token = await self._get_app_only_token(tenant_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(headers=headers) as client:
            user_id = await self._resolve_user_id(client, tenant_id, user_identifier)
            sp_id = await self._get_service_principal_id(client, tenant_id)
            return await self._execute_role_assignment(client, sp_id, user_id, tenant_id)

    async def assign_users_to_app(self, tenant_id: str, user_identifiers: list[str]) -> list[bool]:
        """여러 사용자를 Enterprise Application에 병렬로 할당합니다."""
        if not user_identifiers:
            return []

        token = await self._get_app_only_token(tenant_id)
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            sp_id = await self._get_service_principal_id(client, tenant_id)

            async def _assign_single(user_identifier: str):
                try:
                    user_id = await self._resolve_user_id(client, tenant_id, user_identifier)
                    return await self._execute_role_assignment(client, sp_id, user_id, tenant_id)
                except Exception as e:
                    logger.warning("Failed to assign user in batch", identifier=user_identifier, error=str(e), tenant_id=tenant_id)
                    return False

            return await asyncio.gather(*[_assign_single(u) for u in user_identifiers])

    async def search_users(self, tenant_id: str, query: str = "", skiptoken: str | None = None) -> dict:
        """이름 또는 이메일로 사용자를 검색합니다. (부분 일치 및 페이지네이션 지원)"""
        if not query or len(query) < 2:
            return {"users": [], "has_more": False}

        token = await self._get_app_only_token(tenant_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "ConsistencyLevel": "eventual"
        }
        filter_query = f"startswith(displayName,'{query}') or startswith(mail,'{query}') or startswith(userPrincipalName,'{query}')"
        params = {
            "$filter": filter_query,
            "$select": "id,displayName,mail,userPrincipalName",
            "$top": "10",
            "$count": "true"
        }
        if skiptoken:
            params["$skiptoken"] = skiptoken
        
        logger.info("ExecGraphUserSearch", query=query, params=params, tenant_id=tenant_id)

        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(f"{self.base_url}/users", params=params)
            
            if response.status_code == 403:
                logger.error("Graph API 403 Forbidden during user search", tenant_id=tenant_id)
                raise UnauthorizedException("CONSENT_REQUIRED|테넌트에서 사용자 정보를 검색할 권한이 없습니다.")
            
            if response.status_code != 200:
                logger.error("Failed to search users", code=response.status_code, text=response.text, tenant_id=tenant_id)
                raise Exception(f"사용자 검색 실패: {response.status_code} {response.text}")

            response_json = response.json()
            next_link = response_json.get("@odata.nextLink")
            next_skiptoken = None
            if next_link and "$skiptoken=" in next_link:
                next_skiptoken = next_link.split("$skiptoken=")[1]

            return {
                "users": [
                    {
                        "id": u.get("id"),
                        "name": u.get("displayName") or "Unknown",
                        "email": u.get("mail") or u.get("userPrincipalName")
                    }
                    for u in response_json.get("value", [])
                ],
                "has_more": bool(next_link),
                "next_skiptoken": next_skiptoken,
                "total_count": response_json.get("@odata.count", 0)
            }

    async def _get_app_only_token(self, tenant_id: str) -> str:
        """Client Credentials Flow를 통해 App-only 토큰을 획득합니다."""
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        url = f"{authority}/oauth2/v2.0/token"
        data = {
            "client_id": settings.CLIENT_ID,
            "client_secret": settings.CLIENT_SECRET,
            "grant_type": "client_credentials",
            "scope": "https://graph.microsoft.com/.default"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, data=data)
            if response.status_code != 200:
                logger.error("Failed to get Graph App-only token", error=response.text, tenant_id=tenant_id)
                raise UnauthorizedException(f"CONSENT_REQUIRED|Graph API 인증 실패: {response.text}")
            return response.json()["access_token"]

    async def _get_service_principal_id(self, client: httpx.AsyncClient, tenant_id: str) -> str:
        """현재 앱의 Service Principal ID를 조회합니다."""
        sp_res = await client.get(
            f"{self.base_url}/servicePrincipals",
            params={"$filter": f"appId eq '{settings.CLIENT_ID}'"}
        )
        if sp_res.status_code == 403:
            logger.error("Graph API 403 Forbidden during service principal lookup", tenant_id=tenant_id)
            raise UnauthorizedException(f"CONSENT_REQUIRED|Graph API 권한 부족 (Directory.Read.All): {sp_res.text}")
        if sp_res.status_code != 200 or not sp_res.json().get("value"):
            logger.error("Service Principal not found for this app", tenant_id=tenant_id)
            raise UnauthorizedException("CONSENT_REQUIRED|앱의 Service Principal을 찾을 수 없습니다. 테넌트 등록이 필요합니다.")
        return sp_res.json()["value"][0]["id"]

    async def _resolve_user_id(self, client: httpx.AsyncClient, tenant_id: str, user_identifier: str) -> str:
        """사용자 식별자(UUID 또는 Email)를 바탕으로 Graph User ID(oid)를 반환합니다."""
        if re.match(r"^[0-9a-fA-F-]{36}$", user_identifier):
            return user_identifier

        user_res = await client.get(f"{self.base_url}/users/{user_identifier}")
        if user_res.status_code == 403:
            logger.error("Graph API 403 Forbidden during user lookup", tenant_id=tenant_id)
            raise UnauthorizedException(f"CONSENT_REQUIRED|Graph API 권한 부족 (User.Read.All): {user_res.text}")
        if user_res.status_code != 200:
            logger.error("User not found in Graph", identifier=user_identifier, tenant_id=tenant_id)
            raise UnauthorizedException(f"NOT_FOUND|사용자를 찾을 수 없습니다: {user_identifier}")
        return user_res.json()["id"]

    async def _execute_role_assignment(self, client: httpx.AsyncClient, sp_id: str, user_id: str, tenant_id: str) -> bool:
        """실제 App Role Assignment POST 요청을 실행합니다."""
        assignment_data = {
            "principalId": user_id,
            "resourceId": sp_id,
            "appRoleId": "00000000-0000-0000-0000-000000000000"
        }
        res = await client.post(
            f"{self.base_url}/servicePrincipals/{sp_id}/appRoleAssignments",
            json=assignment_data
        )
        
        if res.status_code == 201:
            logger.info("User successfully assigned to app", user_id=user_id, tenant_id=tenant_id)
            return True
        elif res.status_code == 400 and "already exists" in res.text:
            logger.info("User already assigned", user_id=user_id, tenant_id=tenant_id)
            return True
        
        logger.error("Failed to assign user", error=res.text, tenant_id=tenant_id)
        if res.status_code in [401, 403]:
            raise UnauthorizedException(f"CONSENT_REQUIRED|Graph API 권한 부족 (AppRoleAssignment.ReadWrite.All): {res.text}")
        
        raise UnauthorizedException(f"INTERNAL_ERROR|사용자 할당 실패: {res.text}")