# Tenant Domain

## 정의 (Definition)

Log Doctor 서비스를 이용하는 고객사(Tenant) 정보를 관리하고, 서비스 활성화 상태를 제어하는 핵심 도메인입니다.

## 역할 (Role)

- **테넌트 정보 관리**: MS Teams의 Tenant ID를 기반으로 고객사를 식별하고 정보를 저장합니다.
- **상태 확인**: 특정 테넌트가 정식 등록되었는지, 로그 수집 에이전트가 활성화되었는지 등의 상태를 조회합니다.

## 핵심 유즈케이스 (Core Use Cases)

- `TenantStatusChecker`: 테넌트의 현재 상태(등록 여부, 에이전트 연동 여부 등)를 종합적으로 판단하여 반환합니다.

## 의존성 관계 (Dependencies)

- **Repository**: `CosmosTenantRepository` (Azure Cosmos DB 사용)
- **Infra**: 없음 (순수 데이터 관리 및 도메인 로직)
