from abc import ABC, abstractmethod

# 1. 인터페이스 (규칙)
class AzureRepository(ABC):
    @abstractmethod
    async def get_subscriptions_via_obo(self, sso_token: str) -> list[dict]:
        """프론트엔드의 SSO 토큰을 OBO로 교환하여 구독 목록을 가져옵니다."""
        pass

# 2. 로컬 테스트용 가짜(Mock) 구현체
class MockAzureRepository(AzureRepository):
    async def get_subscriptions_via_obo(self, sso_token: str) -> list[dict]:
        print(f"🔐 [Mock Azure] OBO 토큰 교환 시뮬레이션 완료! (받은 토큰: {sso_token[:10]}...)")
        print(f"☁️ [Mock Azure] 가짜 구독 목록을 반환합니다.")
        
        # 프론트엔드가 UI를 그릴 수 있도록 가짜 구독 리스트를 던져줍니다.
        return [
            {
                "subscription_id": "sub-1111-2222-3333-4444",
                "display_name": "LogDoctor 핵심 인프라 구독",
                "state": "Enabled"
            },
            {
                "subscription_id": "sub-5555-6666-7777-8888",
                "display_name": "개발 테스트용 구독",
                "state": "Enabled"
            }
        ]