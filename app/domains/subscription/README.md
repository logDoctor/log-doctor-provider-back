# Subscription Domain

## 정의 (Definition)

사용자가 소유한 Azure 구독(Subscription) 정보를 조회하고 관리하는 도메인입니다.

## 역할 (Role)

- **구독 목록 조회**: Azure Resource Manager(ARM) API를 연동하여 사용자가 접근 가능한 구독 목록을 가져옵니다.
- **인증 연동 (OBO Flow)**: MS Teams SSO 토큰을 Azure ARM API 호출이 가능한 Access Token으로 교환(On-Behalf-Of)하여 통신합니다.

## 핵심 유즈케이스 (Core Use Cases)

- `SubscriptionFetcher`: 사용자의 토큰을 사용하여 Azure에서 실제 구독 리스트를 가져오는 역할을 수행합니다.

## 의존성 관계 (Dependencies)

- **Repository**: `AzureSubscriptionRepository`
- **Infra**: `app.infra.external.azure_client` (Azure ARM REST API 호출)
