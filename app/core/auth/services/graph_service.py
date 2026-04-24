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
        self._cached_sp_id = None

    async def assign_user_to_app(
        self,
        tenant_id: str,
        user_identifier: str,
        app_role_id: str = "00000000-0000-0000-0000-000000000000",
        sso_token: str | None = None,
    ) -> bool:
        """특정 사용자를 Enterprise Application(Service Principal)에 특정 역할로 할당합니다."""
        token = await self._get_graph_token(tenant_id, sso_token)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(headers=headers) as client:
            user_id = await self._resolve_user_id(client, tenant_id, user_identifier)
            sp_id = await self._get_service_principal_id(client, tenant_id)
            return await self._execute_role_assignment(
                client, sp_id, user_id, tenant_id, app_role_id
            )

    async def assign_users_to_app(
        self,
        tenant_id: str,
        user_identifiers: list[str],
        app_role_id: str = "00000000-0000-0000-0000-000000000000",
        sso_token: str | None = None,
    ) -> list[bool]:
        """여러 사용자를 Enterprise Application에 병렬로 할당합니다."""
        if not user_identifiers:
            return []

        token = await self._get_graph_token(tenant_id, sso_token)
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
                        client, sp_id, user_id, tenant_id, app_role_id
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
        self, tenant_id: str, query: str = "", skiptoken: str | None = None, sso_token: str | None = None
    ) -> dict:
        """이름 또는 이메일로 사용자를 검색합니다. (부분 일치 및 페이지네이션 지원)"""
        if not query or len(query) < 2:
            return {"users": [], "has_more": False}

        token = await self._get_graph_token(tenant_id, sso_token)
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

    async def get_own_service_principal_id(self, tenant_id: str | None = None, sso_token: str | None = None) -> str:
        """현재 서버(앱)의 Service Principal ID를 조회합니다. 조회 결과는 내부에 캐싱됩니다."""
        if self._cached_sp_id:
            return self._cached_sp_id
 
        # tenant_id가 없으면 환경 설정의 TENANT_ID를 사용합니다.
        tid = tenant_id or settings.TENANT_ID
        if not tid:
            raise UnauthorizedException(
                "INTERNAL_ERROR|Tenant ID is required to discover Service Principal ID."
            )
 
        token = await self._get_graph_token(tid, sso_token)
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(headers=headers) as client:
            self._cached_sp_id = await self._get_service_principal_id(client, tid)
            return self._cached_sp_id

    async def list_channels(self, tenant_id: str, team_id: str, sso_token: str | None = None) -> list[dict]:
        """지정된 팀의 채널 목록을 조회합니다."""
        token = await self._get_graph_token(tenant_id, sso_token)
        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(headers=headers) as client:
            res = await client.get(f"{self.base_url}/teams/{team_id}/channels")
            if res.status_code != 200:
                logger.error(
                    "Failed to list channels",
                    team_id=team_id,
                    code=res.status_code,
                    text=res.text,
                )
                return []

            return [
                {"id": c["id"], "name": c["displayName"]}
                for c in res.json().get("value", [])
            ]

    async def send_channel_message(
        self, tenant_id: str, team_id: str, channel_id: str, content: str
    ) -> bool:
        """Teams 채널에 메시지를 전송합니다."""
        token = await self._get_app_only_token(tenant_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # [POLICY] 채널 메시지는 /teams/{teamId}/channels/{channelId}/messages 엔드포인트를 사용합니다.
        url = f"{self.base_url}/teams/{team_id}/channels/{channel_id}/messages"
        payload = {"body": {"content": content}}

        async with httpx.AsyncClient(headers=headers) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 201:
                return True

            logger.error(
                "Failed to send teams channel message",
                team_id=team_id,
                channel_id=channel_id,
                code=res.status_code,
                text=res.text,
            )
            return False

    async def send_activity_notification(
        self, tenant_id: str, user_id: str, topic: dict, preview_text: str
    ) -> bool:
        """사용자의 Teams 활동 피드에 알림을 전송합니다."""
        token = await self._get_app_only_token(tenant_id)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        # Activity Notification을 위해서는 App Manifest에 정의된 notificationId가 필요함
        # 여기서는 'analysisCompleted'라고 가정 (실제 매니페스트와 일치해야 함)
        payload = {
            "topic": topic,
            "activityType": "analysisCompleted",
            "previewText": {"content": preview_text},
            "templateParameters": [
                {"name": "analysisResult", "value": preview_text},
            ],
        }

        url = f"{self.base_url}/users/{user_id}/teamwork/sendActivityNotification"

        async with httpx.AsyncClient(headers=headers) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 204:  # 성공 시 204 No Content
                return True

            logger.error(
                "Failed to send activity notification",
                user_id=user_id,
                code=res.status_code,
                text=res.text,
            )
            return False

    async def list_joined_teams(self, tenant_id: str, sso_token: str | None = None) -> list[dict]:
        """사용자가 속한 테넌트의 모든 팀 목록을 조회합니다."""
        # [POLICY] 403/401은 권한 문제이므로 재시도 없이 즉시 에러 반환.
        # 재시도는 일시적 오류(5xx, 네트워크 오류)에만 적용합니다.
        for attempt in range(3):
            try:
                token = await self._get_graph_token(tenant_id, sso_token)
                headers = {"Authorization": f"Bearer {token}"}

                async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
                    res1 = await client.get(f"{self.base_url}/teams")

                    if res1.status_code == 200:
                        return [
                            {"id": t.get("id"), "name": t.get("displayName") or "Unknown"}
                            for t in res1.json().get("value", [])
                        ]

                    # 403/401은 권한 문제 → 재시도 불필요, 즉시 에러
                    if res1.status_code in (401, 403):
                        logger.error(
                            "Graph API permission denied on GET /teams",
                            tenant_id=tenant_id,
                            status=res1.status_code,
                            body=res1.text,
                            hint="Ensure 'Team.ReadBasic.All' is granted in Azure AD App Registration (prod).",
                        )
                        raise UnauthorizedException(
                            f"CONSENT_REQUIRED|Missing Graph API permission for /teams "
                            f"(status={res1.status_code}). "
                            f"Grant 'Team.ReadBasic.All' or 'Group.Read.All' Admin Consent in prod App Registration."
                        )

                    logger.warning(
                        "GET /teams returned unexpected status, falling back to /groups",
                        attempt=attempt + 1,
                        status=res1.status_code,
                    )

                    res2 = await client.get(
                        f"{self.base_url}/groups",
                        params={"$filter": "resourceProvisioningOptions/Any(x:x eq 'Team')"},
                    )

                    if res2.status_code == 200:
                        return [
                            {"id": g.get("id"), "name": g.get("displayName") or "Unknown"}
                            for g in res2.json().get("value", [])
                        ]

                    # /groups 도 403/401 → 즉시 에러
                    if res2.status_code in (401, 403):
                        logger.error(
                            "Graph API permission denied on GET /groups (teams fallback)",
                            tenant_id=tenant_id,
                            status=res2.status_code,
                            body=res2.text,
                            hint="Ensure 'Group.Read.All' is granted in Azure AD App Registration (prod).",
                        )
                        raise UnauthorizedException(
                            f"CONSENT_REQUIRED|Missing Graph API permission for /groups "
                            f"(status={res2.status_code}). "
                            f"Grant 'Group.Read.All' Admin Consent in prod App Registration."
                        )

                    logger.warning(
                        "Teams list attempt failed (both endpoints returned non-200/non-403)",
                        attempt=attempt + 1,
                        teams_status=res1.status_code,
                        groups_status=res2.status_code,
                    )

            except UnauthorizedException:
                # 권한 에러는 재시도 없이 바로 상위로 전파
                raise
            except Exception as e:
                logger.warning("Exception during teams search", attempt=attempt + 1, error=str(e))

            if attempt < 2:  # 마지막 시도가 아니라면 대기 후 재시도
                await asyncio.sleep(2)

        logger.error(
            "All attempts to list teams failed. May be a transient Graph API error.",
            tenant_id=tenant_id,
        )
        raise UnauthorizedException(
            "CONSENT_PROPAGATING|Azure AD permissions are propagating. Please refresh in a few seconds."
        )

    async def _get_app_only_token(self, tenant_id: str) -> str:
        """TokenProvider를 통해 Graph용 앱 전용 토큰을 획득합니다."""
        return await self.token_provider.get_app_token(
            tid=tenant_id, scopes=["https://graph.microsoft.com/.default"]
        )

    async def _get_graph_token(self, tenant_id: str, sso_token: str | None = None) -> str:
        """OBO 토큰 혹은 앱 토큰 중 상황에 맞는 토큰을 반환합니다."""
        # [POLICY] 빈 문자열은 None과 동일하게 처리합니다.
        # 프론트엔드가 인증 전에 "Bearer " (빈 토큰)를 전송하는 경우를 방어합니다.
        effective_sso_token = sso_token if sso_token and sso_token.strip() else None
        if effective_sso_token:
            return await self.token_provider.get_obo_token(
                effective_sso_token, scopes=["https://graph.microsoft.com/.default"]
            )
        return await self._get_app_only_token(tenant_id)

    async def _get_service_principal_id(
        self, client: httpx.AsyncClient | None = None, tenant_id: str | None = None
    ) -> str:
        """현재 앱의 Service Principal ID를 조회합니다."""
        if client is None:
            if not tenant_id:
                raise ValueError("tenant_id is required if client is not provided")
            token = await self._get_app_only_token(tenant_id)
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"}
            ) as new_client:
                return await self._get_service_principal_id(new_client, tenant_id)

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
        self, tenant_id: str, emails: list[str], sso_token: str | None = None
    ) -> list[dict[str, str]]:
        """이메일 리스트를 받아서 [{"email": "...", "user_id": "..."}] 리스트를 반환합니다."""
        if not emails:
            return []

        token = await self._get_graph_token(tenant_id, sso_token)
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            tasks = []
            for email in emails:
                tasks.append(self._resolve_user_id(client, tenant_id, email, sso_token))

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
        self, client: httpx.AsyncClient, tenant_id: str, user_identifier: str, sso_token: str | None = None
    ) -> str:
        """사용자 식별자(UUID 또는 Email)를 바탕으로 Graph User ID(oid)를 반환합니다."""
        if re.match(r"^[0-9a-fA-F-]{36}$", user_identifier):
            return user_identifier

        # 만약 클라이언트가 전달되지 않았다면 새로 생성하여 처리 (재귀 호출 활용)
        if client is None:
            token = await self._get_graph_token(tenant_id, sso_token)
            async with httpx.AsyncClient(headers={"Authorization": f"Bearer {token}"}) as new_client:
                return await self._resolve_user_id(new_client, tenant_id, user_identifier, sso_token)

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
        self,
        client: httpx.AsyncClient,
        sp_id: str,
        user_id: str,
        tenant_id: str,
        app_role_id: str,
    ) -> bool:
        """실제 App Role Assignment POST 요청을 실행합니다."""
        assignment_data = {
            "principalId": user_id,
            "resourceId": sp_id,
            "appRoleId": app_role_id,
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

    async def check_global_admins(
        self, tenant_id: str, guids: list[str], sso_token: str | None = None
    ) -> set[str]:
        """
        주어진 사용자 GUID 목록 중 전역 관리자(Global Administrator) 역할을 보유한
        사용자의 GUID set을 반환합니다. (Microsoft Graph /users/{id}/memberOf 활용)
        """
        # Azure AD 전역 관리자 역할 Template ID
        global_admin_role_id = "62e90394-69f5-4237-9190-012177145e10"

        if not guids:
            return set()

        token = await self._get_graph_token(tenant_id, sso_token)
        headers = {"Authorization": f"Bearer {token}"}

        global_admins: set[str] = set()

        async with httpx.AsyncClient(headers=headers, timeout=10.0) as client:
            async def _check_one(guid: str) -> bool:
                try:
                    res = await client.get(
                        f"{self.base_url}/users/{guid}/memberOf/microsoft.graph.directoryRole",
                        params={"$select": "roleTemplateId"},
                    )
                    if res.status_code != 200:
                        return False
                    roles = res.json().get("value", [])
                    return any(
                        r.get("roleTemplateId", "").lower() == global_admin_role_id
                        for r in roles
                    )
                except Exception:
                    return False

            results = await asyncio.gather(*[_check_one(g) for g in guids])
            for guid, is_admin in zip(guids, results, strict=True):
                if is_admin:
                    global_admins.add(guid)

        return global_admins

