from fastapi import Depends

from .repository import MockTenantRepository, CosmosTenantRepository, TenantRepository
from .usecases.get_tenant_status_use_case import GetTenantStatusUseCase
from .azure_repository import AzureRepository, MockAzureRepository
from .usecases.get_subscriptions_use_case import GetSubscriptionsUseCase


# ==========================================
# 1. 기존 조립 라인 (테넌트 상태 조회용) - 유지
# ==========================================
def get_tenant_repository() -> TenantRepository:
    """Returns the concrete implementation of TenantRepository."""
    return MockTenantRepository()

def get_tenant_status_use_case(
    repository: TenantRepository = Depends(get_tenant_repository),
) -> GetTenantStatusUseCase:
    """Returns a GetTenantStatusUseCase instance with the injected repository."""
    return GetTenantStatusUseCase(repository)


# ==========================================
# 2. 🌟 신규 조립 라인 (OBO 구독 목록 조회용)
# ==========================================
def get_azure_repository() -> AzureRepository:
    """외부 Azure 통신용 부품을 결정합니다. (지금은 로컬 테스트용 Mock 반환)"""
    return MockAzureRepository()

def get_subscriptions_use_case(
    azure_repository: AzureRepository = Depends(get_azure_repository),
) -> GetSubscriptionsUseCase:
    """Mock Azure 부품을 구독 조회 유즈케이스(두뇌)에 꽂아서 반환합니다."""
    return GetSubscriptionsUseCase(azure_repository)