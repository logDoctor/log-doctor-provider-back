import asyncio
import re

import httpx
import structlog

from app.core.auth.services.auth_provider import TokenProvider
from app.core.config import settings
from app.core.exceptions import UnauthorizedException

logger = structlog.get_logger()


class GraphService:
    """Microsoft Graph API를 통해 Entra ID 리소스를 관리하는 서비스"""

    def __init__(self, token_provider: TokenProvider):
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.token_provider = token_provider

    async def assign_user_to_app(self, tenant_id: str, user_identifier: str) -> bool:
        """특정 사용자를 Enterprise Application(Service Principal)에 할당합니다."""
        token = await self._get_app_only_token(tenant_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(headers=headers) as client:
            user_id = await self._resolve_user_id(client, tenant_id, user_identifier)
            sp_id = await self._get_service_principal_id(client, tenant_id)
            return await self._execute_role_assignment(
                client, sp_id, user_id, tenant_id
            )

    async def assign_users_to_app(
        self, tenant_id: str, user_identifiers: list[str]
    ) -> list[bool]:
        """여러 사용자를 Enterprise Application에 병렬로 할당합니다."""
        if not user_identifiers:
            return []

        token = await self._get_app_only_token(tenant_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
            sp_id = await self._get_service_principal_id(client, tenant_id)

            async def _assign_single(user_identifier: str):
                try:
                    user_id = await self._resolve_user_id(
                        client, tenant_id, user_identifier
                    )
                    return await self._execute_role_assignment(
                        client, sp_id, user_id, tenant_id
                    )
                except Exception as e:
                    logger.warning(
                        "Failed to assign user in batch",
                        identifier=user_identifier,
                        error=str(e),
                        tenant_id=tenant_id,
                    )
                    return False

            return await asyncio.gather(*[_assign_single(u) for u in user_identifiers])

    async def search_users(
        self, tenant_id: str, query: str = "", skiptoken: str | None = None
    ) -> dict:
        """이름 또는 이메일로 사용자를 검색합니다. (부분 일치 및 페이지네이션 지원)"""
        if not query or len(query) < 2:
            return {"users": [], "has_more": False}

        token = await self._get_app_only_token(tenant_id)
        headers = {"Authorization": f"Bearer {token}", "ConsistencyLevel": "eventual"}
        filter_query = f"startswith(displayName,'{query}') or startswith(mail,'{query}') or startswith(userPrincipalName,'{query}')"
        params = {
            "$filter": filter_query,
            "$select": "id,displayName,mail,userPrincipalName",
            "$top": "10",
            "$count": "true",
        }
        if skiptoken:
            params["$skiptoken"] = skiptoken

        logger.info(
            "ExecGraphUserSearch", query=query, params=params, tenant_id=tenant_id
        )

        async with httpx.AsyncClient(headers=headers) as client:
            response = await client.get(f"{self.base_url}/users", params=params)

            if response.status_code == 403:
                logger.error(
                    "Graph API 403 Forbidden during user search", tenant_id=tenant_id
                )
                raise UnauthorizedException(
                    "CONSENT_REQUIRED|Unauthorized to search user information in the tenant."
                )

            if response.status_code != 200:
                logger.error(
                    "Failed to search users",
                    code=response.status_code,
                    text=response.text,
                    tenant_id=tenant_id,
                )
                raise Exception(
                    f"User search failed: {response.status_code} {response.text}"
                )

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
                        "email": u.get("mail") or u.get("userPrincipalName"),
                    }
                    for u in response_json.get("value", [])
                ],
                "has_more": bool(next_link),
                "next_skiptoken": next_skiptoken,
                "total_count": response_json.get("@odata.count", 0),
            }

    async def _get_app_only_token(self, tenant_id: str) -> str:
        """TokenProvider를 통해 Graph용 앱 전용 토큰을 획득합니다."""
        return await self.token_provider.get_app_token(
            tid=tenant_id, scopes=["https://graph.microsoft.com/.default"]
        )

    async def _get_service_principal_id(
        self, client: httpx.AsyncClient, tenant_id: str
    ) -> str:
        """현재 앱의 Service Principal ID를 조회합니다."""
        sp_res = await client.get(
            f"{self.base_url}/servicePrincipals",
            params={"$filter": f"appId eq '{settings.CLIENT_ID}'"},
        )
        if sp_res.status_code == 403:
            logger.error(
                "Graph API 403 Forbidden during service principal lookup",
                tenant_id=tenant_id,
            )
            raise UnauthorizedException(
                f"CONSENT_REQUIRED|Insufficient Graph API permissions (Directory.Read.All): {sp_res.text}"
            )
        if sp_res.status_code != 200 or not sp_res.json().get("value"):
            logger.error(
                "Service Principal not found for this app", tenant_id=tenant_id
            )
            raise UnauthorizedException(
                "CONSENT_REQUIRED|Service Principal for the app not found. Tenant registration is required."
            )
        return sp_res.json()["value"][0]["id"]

    async def resolve_user_ids(
        self, tenant_id: str, emails: list[str]
    ) -> list[dict[str, str]]:
        """이메일 리스트를 받아서 [{"email": "...", "user_id": "..."}] 리스트를 반환합니다."""
        if not emails:
            return []

        token = await self._get_app_only_token(tenant_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            tasks = []
            for email in emails:
                tasks.append(self._resolve_user_id(client, tenant_id, email))

            resolved_ids = await asyncio.gather(*tasks, return_exceptions=True)

            results = []
            for email, res in zip(emails, resolved_ids, strict=True):
                if isinstance(res, str):
                    results.append({"email": email, "user_id": res})
                else:
                    logger.error(
                        "Failed to resolve mandatory user id",
                        email=email,
                        error=str(res),
                    )
                    if isinstance(res, Exception):
                        raise res
                    raise UnauthorizedException(
                        f"NOT_FOUND|Operator account information not found: {email}"
                    )

        return results

    async def _resolve_user_id(
        self, client: httpx.AsyncClient, tenant_id: str, user_identifier: str
    ) -> str:
        """사용자 식별자(UUID 또는 Email)를 바탕으로 Graph User ID(oid)를 반환합니다."""
        if re.match(r"^[0-9a-fA-F-]{36}$", user_identifier):
            return user_identifier

        user_res = await client.get(f"{self.base_url}/users/{user_identifier}")
        if user_res.status_code == 403:
            logger.error(
                "Graph API 403 Forbidden during user lookup", tenant_id=tenant_id
            )
            raise UnauthorizedException(
                f"CONSENT_REQUIRED|Insufficient Graph API permissions (User.Read.All): {user_res.text}"
            )
        if user_res.status_code != 200:
            logger.error(
                "User not found in Graph",
                identifier=user_identifier,
                tenant_id=tenant_id,
            )
            raise UnauthorizedException(f"NOT_FOUND|User not found: {user_identifier}")
        return user_res.json()["id"]

    async def _execute_role_assignment(
        self, client: httpx.AsyncClient, sp_id: str, user_id: str, tenant_id: str
    ) -> bool:
        """실제 App Role Assignment POST 요청을 실행합니다."""
        assignment_data = {
            "principalId": user_id,
            "resourceId": sp_id,
            "appRoleId": "00000000-0000-0000-0000-000000000000",
        }
        res = await client.post(
            f"{self.base_url}/servicePrincipals/{sp_id}/appRoleAssignments",
            json=assignment_data,
        )

        if res.status_code == 201:
            logger.info(
                "User successfully assigned to app",
                user_id=user_id,
                tenant_id=tenant_id,
            )
            return True
        elif res.status_code == 400 and "already exists" in res.text:
            logger.info("User already assigned", user_id=user_id, tenant_id=tenant_id)
            return True

        logger.error("Failed to assign user", error=res.text, tenant_id=tenant_id)
        if res.status_code in [401, 403]:
            raise UnauthorizedException(
                f"CONSENT_REQUIRED|Insufficient Graph API permissions (AppRoleAssignment.ReadWrite.All): {res.text}"
            )

        raise UnauthorizedException(f"INTERNAL_ERROR|Failed to assign user: {res.text}")
