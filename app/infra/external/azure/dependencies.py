from functools import lru_cache

from fastapi import Depends

from app.core.auth.dependencies import get_azure_credential, get_token_provider
from app.core.interfaces.azure_arm import AzureArmService
from app.core.interfaces.azure_queue import AzureQueueService
from app.core.logging import get_logger

from .clients import AzureArmClient, AzureQueueClient
from .services import AzureArmServiceImpl, AzureQueueServiceImpl


@lru_cache
def get_azure_arm_client() -> AzureArmClient:
    return AzureArmClient()


@lru_cache
def get_azure_queue_client() -> AzureQueueClient:
    return AzureQueueClient()


@lru_cache
def get_azure_arm_service(
    token_provider=Depends(get_token_provider),
    arm_client=Depends(get_azure_arm_client),
) -> AzureArmService:
    logger = get_logger("azure_arm_service")
    return AzureArmServiceImpl(token_provider, arm_client, logger)


@lru_cache
def get_azure_queue_service(
    credential=Depends(get_azure_credential),
    queue_client=Depends(get_azure_queue_client),
) -> AzureQueueService:
    logger = get_logger("azure_queue_service")
    return AzureQueueServiceImpl(credential, queue_client, logger)
