import json

import structlog
from azure.core.credentials import TokenCredential
from azure.identity.aio import ClientSecretCredential, ManagedIdentityCredential

from app.core.interfaces.azure_queue import AzureQueueService
from app.infra.external.azure.clients import AzureStorageQueueClient


class AzureQueueServiceImpl(AzureQueueService):
    """Azure Storage Queue 기반 서비스 구현체"""

    def __init__(
        self,
        credential: TokenCredential,
        queue_client: AzureStorageQueueClient,
        logger: structlog.BoundLogger,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.credential = credential
        self.queue_client = queue_client
        self.logger = logger
        self.client_id = client_id
        self.client_secret = client_secret

    async def push(
        self,
        account_name: str,
        queue_name: str,
        message: dict,
        tenant_id: str | None = None,
    ) -> None:
        """에이전트 테넌트의 스토리지 큐에 메시지를 전송합니다."""
        target_credential = self.credential
        temp_credential = None

        if tenant_id:
            if self.client_id and self.client_secret:
                # 테넌트가 명시된 경우 ClientSecretCredential을 사용하여 해당 테넌트로부터 '해당 테넌트가 발행한 토큰(Issuer match)'을 획득합니다.
                self.logger.info(
                    "Using ClientSecretCredential for cross-tenant authentication",
                    tenant_id=tenant_id,
                    client_id=self.client_id,
                )
                temp_credential = ClientSecretCredential(
                    tenant_id=tenant_id,
                    client_id=self.client_id,
                    client_secret=self.client_secret,
                )
            else:
                self.logger.info(
                    "Falling back to ManagedIdentityCredential for cross-tenant authentication",
                    tenant_id=tenant_id,
                )
                temp_credential = ManagedIdentityCredential(tenant_id=tenant_id)
            target_credential = temp_credential

        try:
            async with self.queue_client.get_queue_client(
                account_name=account_name,
                queue_name=queue_name,
                credential=target_credential,
            ) as client:
                await client.send_message(json.dumps(message).encode("utf-8"))
        except Exception as e:
            if "AuthorizationPermissionMismatch" in str(e):
                self.logger.error(
                    "RBAC_ROLE_ASSIGNMENT_REQUIRED",
                    error="AuthorizationPermissionMismatch",
                    message="The Service Principal does not have 'Storage Queue Data Message Sender' role on the target storage account.",
                    tenant_id=tenant_id,
                    client_id=self.client_id,
                    storage_account=account_name,
                )
            raise
        finally:
            if temp_credential:
                await temp_credential.close()
