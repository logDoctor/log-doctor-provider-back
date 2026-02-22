from fastapi import Depends

from .repository import CosmosTenantRepository, TenantRepository
from .usecases.tenant_status_checker import (
    TenantStatusChecker,
)  # 이름 변경된 유즈케이스
from .azure_repository import AzureRepository, MockAzureRepository
from .usecases.subscription_fetcher import SubscriptionFetcher  # 이름 변경된 유즈케이스
from .usecases.tenant_onboarder import TenantOnboarder  # 이름 변경된 유즈케이스


# ==========================================
# CosmosDB로 교체
# ==========================================
def get_tenant_repository() -> TenantRepository:
    return CosmosTenantRepository()  # DB 연결


# 이하 NounVerber 이름으로 교체된 DI 주입기
def get_tenant_status_checker(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantStatusChecker:
    return TenantStatusChecker(repository)


def get_azure_repository() -> AzureRepository:
    return MockAzureRepository()


def get_subscription_fetcher(
    azure_repository: AzureRepository = Depends(get_azure_repository),
) -> SubscriptionFetcher:
    return SubscriptionFetcher(azure_repository)


def get_tenant_onboarder(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> TenantOnboarder:
    return TenantOnboarder(repository)
