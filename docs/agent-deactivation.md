# 에이전트 비활성화 (Deactivation) 설계 문서

## 1. 개요

에이전트 비활성화는 고객사 Azure 리소스 그룹을 삭제하고, 백엔드 DB에서 소프트 딜리트 처리하는 기능입니다.

### 핵심 원칙

- **안전한 2단계 삭제**: Azure 리소스 삭제 확인 후 DB 상태 전환
- **비동기 처리**: API 즉시 반환 → 프론트 폴링으로 완료 확인
- **서비스 추상화**: `AzureResourceService` 인터페이스로 인프라 계층 분리

---

## 2. API 설계

| API                                | 메서드 | 역할                                   | 인증             |
| :--------------------------------- | :----- | :------------------------------------- | :--------------- |
| `/v1/agents/{id}`                  | DELETE | Azure 삭제 요청 + `DEACTIVATING` 마킹  | OBO 토큰         |
| `/v1/agents/{id}/azure-status`     | GET    | 리소스 그룹 존재 여부 확인 (순수 읽기) | Managed Identity |
| `/v1/agents/{id}/confirm-deletion` | POST   | `DELETED` 최종 전환                    | Managed Identity |

### 토큰 전략

- **DELETE (Phase 1)**: 사용자 세션이 유효한 시점에 OBO 토큰을 교환하여 ARM API 호출
- **GET/POST (Phase 2)**: Managed Identity로 수행 — 사용자 세션과 무관하게 동작

---

## 3. 상태 전이

```
ACTIVE / INITIALIZING
    ↓ DELETE API (Phase 1)
DEACTIVATING
    ↓ POST confirm-deletion (Phase 2, Azure 삭제 확인 후)
DELETED (soft-delete, deleted_at 기록)

DEACTIVATING → DEACTIVATE_FAILED (Azure 삭제 에러 시)
DEACTIVATE_FAILED → DEACTIVATING (재시도 시)
```

---

## 4. 처리 흐름

### Phase 1: 삭제 요청

1. 운영자가 "에이전트 제거" 클릭 → 확인 Dialog
2. `DELETE /v1/agents/{id}?tenant_id=...&delete_azure_resources=true`
3. 백엔드: OBO 토큰 교환 → ARM API로 리소스 그룹 삭제 요청 (202 Accepted)
4. 에이전트 상태 `DEACTIVATING` → DB 저장 → **즉시 202 반환**

### Phase 2: 삭제 확인

5. 프론트엔드: `DEACTIVATING` 감지 → 5초 간격으로 `GET /agents/{id}/azure-status` 폴링
6. `{ exists: false }` 수신 → `POST /agents/{id}/confirm-deletion` 호출
7. 에이전트 상태 `DELETED`, `deleted_at` 기록 → 목록에서 제외

### 방어 로직 (Safety Net)

- 에이전트 목록 로드 시 `DEACTIVATING` 상태 에이전트가 있으면 자동으로 폴링 시작
- 브라우저 닫고 재접속해도 삭제 확인이 자연스럽게 재개됨

---

## 5. 실패 시나리오 및 복구

| 시나리오                         | 결과                | 복구 방법                              |
| :------------------------------- | :------------------ | :------------------------------------- |
| Azure DELETE 요청 실패           | `DEACTIVATE_FAILED` | 재시도 버튼 → DELETE API 재호출        |
| Azure 삭제 중 브라우저 닫힘      | `DEACTIVATING` 유지 | 재접속 시 방어 로직이 자동 폴링 재개   |
| Azure 삭제 완료 but confirm 실패 | `DEACTIVATING` 유지 | 다음 azure-status 폴링에서 자동 재시도 |
| 리소스 그룹이 이미 없음          | 즉시 `DELETED`      | Phase 1에서 바로 처리                  |

---

## 6. 인프라 계층

### AzureResourceService (Interface)

```python
class AzureResourceService(ABC):
    async def delete_resource_group(self, access_token, sub_id, rg_name) -> str
    async def check_resource_group_exists(self, sub_id, rg_name) -> bool
```

- `delete_resource_group`: OBO 토큰 기반, `AzureRestClient` 활용
- `check_resource_group_exists`: `DefaultAzureCredential` (Managed Identity) 활용
  - 실패 시 안전하게 `True` (존재) 반환하여 조기 삭제 확정 방지
