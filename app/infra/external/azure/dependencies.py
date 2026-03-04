from .azure_resource_service import AzureResourceService, AzureResourceServiceImpl


def get_azure_resource_service() -> AzureResourceService:
    return AzureResourceServiceImpl()
