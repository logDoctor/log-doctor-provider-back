# Entra ID 앱 등록 관리 메모

## 앱 식별자

| 항목 | 값 |
|------|-----|
| 앱 이름 | logdoctor |
| Application ID (Client ID) | `441b4d0e-a91f-4e3a-8f88-07a492e982aa` |
| Service Principal Object ID | `ce728223-e76e-44a3-8af0-1b44955b6d7e` |
| App Registration Object ID | `az ad app show --id 441b4d0e-a91f-4e3a-8f88-07a492e982aa --query id -o tsv` 로 확인 |

> App Registration Object ID는 계정마다 다를 수 있으므로 위 명령어로 직접 확인할 것

---

## servicePrincipalLockConfiguration 해제

**이 속성은 App Registration에 있음 (Service Principal이 아님)**

```bash
# 1. App Registration Object ID 확인
az ad app show --id 441b4d0e-a91f-4e3a-8f88-07a492e982aa --query id -o tsv

# 2. 잠금 해제
az rest --method PATCH \
  --url "https://graph.microsoft.com/v1.0/applications/<위에서 나온 id>" \
  --body '{"servicePrincipalLockConfiguration": {"isEnabled": false}}'
```

---

## Bicep 배포

- 앱 등록은 리소스 그룹에 속하지 않음 (Entra ID / 테넌트 레벨 리소스)
- Bicep Graph extension 배포 시 scope 지정이 필요함 (Azure CLI 제약)
- 배포 명령어는 직접 테스트 후 확인 필요

```bash
# 문법 검증 (확인됨)
az bicep build --file log-doctor-provider-back/entra-id.bicep
```

---

## Admin Consent

권한 변경 후 아래 4개 Delegated 권한에 대해 관리자 동의 필요:

- `AppRoleAssignment.ReadWrite.All`
- `RoleManagement.Read.Directory`
- `User.Read.All`
- `Application.Read.All`

**Portal 경로:** Entra ID → 앱 등록 → logdoctor → API 사용 권한 → 관리자 동의 허용

---

## Portal에서 설정해야 할 최종 권한 목록

### Microsoft Graph — Delegated (위임됨)

| 권한 | 상태 | 사용 이유 |
|------|------|-----------|
| `User.Read` | 이미 있음 | Teams SSO 로그인 사용자 기본 프로필 취득 |
| `User.Read.All` | 추가 필요 | 테넌트 등록 시 운영자 이메일 → 사용자 ID 변환 (`GET /users/{email}`) |
| `AppRoleAssignment.ReadWrite.All` | 추가 필요 | 테넌트 등록 시 관리자·운영자에게 TenantAdmin/PrivilegedUser 역할 부여 (`POST /servicePrincipals/{id}/appRoleAssignments`) |
| `RoleManagement.Read.Directory` | 추가 필요 | 로그인한 사용자가 Global Admin인지 확인 (`GET /users/{id}/memberOf/directoryRole`) |
| `Application.Read.All` | 추가 필요 | 테넌트 등록 시 고객사 테넌트 내 앱의 Service Principal ID 조회 (`GET /servicePrincipals?$filter=appId eq '...'`) |

### Microsoft Graph — Application (애플리케이션)

| 권한 | 상태 | 사용 이유 |
|------|------|-----------|
| `Group.Read.All` | 추가 필요 | 백그라운드에서 고객사 Teams 목록 및 채널 열거 (`GET /teams`, `GET /groups?$filter=Team`) |
| `TeamsActivity.Send` | 추가 필요 | 진단 완료 시 Teams 사용자에게 알림 전송 (`POST /users/{id}/teamwork/sendActivityNotification`) |

### Azure Service Management API — Delegated (위임됨)

| 권한 | 상태 | 사용 이유 |
|------|------|-----------|
| `user_impersonation` | 추가 필요 | 로그인한 사용자의 Azure 구독·리소스 그룹 조회 및 에이전트 배포 정보 취득 |

---

> 위 권한 추가 후 **관리자 동의(Admin Consent)** 필요
