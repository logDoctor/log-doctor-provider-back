# Security Guards & Decorators Guide

이 패키지는 Log Doctor 백엔드의 보안 정책을 선언적으로 적용하기 위한 가드와 데코레이터를 제공합니다.

## Quick Reference Table

| 데코레이터           | 용도                       | 자동 주입 인자       | 주요 에러        |
| :------------------- | :------------------------- | :------------------- | :--------------- |
| `@token_required`    | 유효한 SSO 토큰 존재 확인  | 없음                 | 401 Unauthorized |
| `@identity_required` | 호출자 신원(Identity) 식별 | `identity: Identity` | 401 Unauthorized |
| `@admin_required`    | 관리자 권한(`ADMIN`) 확인  | 없음                 | 403 Forbidden    |
| `@tenant_verified`   | 테넌트 ID 정합성 검증      | `tenant_id: str`     | 403 Forbidden    |

---

## Usage Examples

### 1. `@token_required`

단순히 로그인이 되어 있는지만 확인하고 싶을 때 사용합니다.

```python
@router.get("/public-data")
@token_required
async def get_data():
    return {"status": "authorized"}
```

### 2. `@identity_required`

누가 호출했는지 정보가 필요할 때 사용합니다. `identity`라는 이름의 인자가 있으면 자동으로 객체를 넣어줍니다.

```python
@router.get("/me")
@identity_required
async def get_my_profile(identity: Identity):
    return identity
```

### 3. `@admin_required`

운영자 권한이 필요한 민감한 API에 사용합니다.

```python
@router.post("/config")
@admin_required
async def update_config(data: dict):
    # 관리자만 진입 가능
    return {"message": "updated"}
```

### 4. `@tenant_verified`

에이전트로부터 오는 요청의 테넌트 ID가 토큰의 정보와 일치하는지 검증합니다. `tenant_id` 인자에 검증된 값을 넣어줍니다.

```python
@router.post("/logs")
@tenant_verified
async def upload_logs(tenant_id: str, logs: list):
    # 검증된 tenant_id를 사용하여 격리된 저장소에 저장
    return {"tenant": tenant_id, "count": len(logs)}
```

---

## Design Principles

1. **Decoupled Logic**: 검증 알맹이는 `services/`의 Verifier 클래스에 있으며, 가드는 이를 FastAPI 환경에 매핑만 합니다.
2. **Declarative Style**: `Depends` 구문을 숨기고 데코레이터를 통해 라우터의 가독성을 높입니다.
3. **Fail-fast**: 인증/인가 실패 시 즉시 적절한 HTTP 예외를 발생시킵니다.
