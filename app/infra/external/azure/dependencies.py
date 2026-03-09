from fastapi import Depends

from app.core.auth.dependencies import get_token_provider

from .azure_resource_service import AzureResourceService, AzureResourceServiceImpl


def get_azure_resource_service(
    token_provider=Depends(get_token_provider),
) -> AzureResourceService:
    return AzureResourceServiceImpl(token_provider)
