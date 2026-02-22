# 환경변수(.env) 설정 가이드 (로컬 개발 환경 기준)

본 문서는 Teams 앱 프론트엔드와 Log Doctor 백엔드가 로컬 환경에서 정상적으로 통신하고, Azure 리소스(MFA 이슈 우회)에 접근하기 위해 설정된 환경변수의 최종 상태와 그 원리를 정리한 문서입니다.

---

## 1. 프론트엔드 (Teams App) 설정
- **위치:** `log-doctor-provider-front/env/.env.local`
- **목적:** Teams 안에서 실행되는 React 화면이 사용자(예: `chjcmy@logdoctor.onmicrosoft.com`)를 인증하고, 백엔드로 넘겨줄 기초 SSO 토큰을 받아오기 위한 설정입니다.
- **핵심:** 권한 부족 에러를 피하기 위해 팀장님의 운영용 앱(`2bc3...`)이 아닌, Teams Toolkit이 내 로컬 전용으로 만들어준 무료 앱(`logdoctorlocal`) 자격 증명을 사용합니다.

```dotenv
# Teams 앱이 연결될 로컬 주소 (백엔드가 아닙니다)
TAB_DOMAIN=localhost
SSO_DOMAIN=localhost:53000
TAB_ENDPOINT=https://localhost:53000

# [중요] 내 로컬 전용으로 생성된 Azure AD 앱 (logdoctorlocal) 정보
# 이 값이 백엔드의 CLIENT_ID와 반드시 일치해야 합니다!
AAD_APP_CLIENT_ID=6880f4e3-6c6f-4865-a16e-f2cd081a3f9d
AAD_APP_OBJECT_ID=5b08878f-0ba8-42b5-bd31-3d17d9e545b6

# 인증을 제공하는 주최자 (Log Doctor의 M365 회사 테넌트 ID)
AAD_APP_TENANT_ID=ccdcba04-0a62-4e96-9964-dc1fc61279f8
AAD_APP_OAUTH_AUTHORITY=https://login.microsoftonline.com/ccdcba04-0a62-4e96-9964-dc1fc61279f8
AAD_APP_OAUTH_AUTHORITY_HOST=https://login.microsoftonline.com
```

---

## 2. 백엔드 (FastAPI) 설정
- **위치:** `log-doctor-provider-back/.env`
- **목적:** 프론트엔드에서 넘어온 토큰을 까서 "위조되지 않은 진짜 토큰이 맞는지" 검증하고, Azure 클라우드(DB나 구독 목록)에서 데이터를 퍼오기 위한 설정입니다.
- **핵심:** `AUTH_METHOD`를 `managed_identity`로 설정하여, MFA 보안 에러(AADSTS50076)가 터지는 OBO 교환 비극을 차단하고, 내 터미널(`azd auth login`)에 로그인된 강력한 인증서를 직통으로 사용합니다.

```dotenv
# --- 보안 및 서버 기본 설정 ---
# 프론트엔드가 접속할 백엔드 주소 (CORS용)
FRONTEND_URL=https://localhost:53000
ENVIRONMENT=development

# --- 인증 설정 ---
# [핵심] MFA 우회를 위해 secret(OBO) 대신 azd 커맨드의 인증서를 흡수하는 방식 사용
AUTH_METHOD=managed_identity

# Azure AD (Entra ID) 설정
# Token Validation 시 프론트엔드와 일치하는지 검사하는 용도 (필수)
CLIENT_ID=6880f4e3-6c6f-4865-a16e-f2cd081a3f9d
TENANT_ID=ccdcba04-0a62-4e96-9964-dc1fc61279f8

# (AUTH_METHOD=managed_identity 이므로 현재 로컬에서는 사용되지 않으나, 추후 OBO 부활 대비용)
CLIENT_SECRET=hRQ8Q~1UlcabNM-wYRK6NnByCT0n7YQ49YIkGbVU

# --- 데이터베이스 설정 (Cosmos DB Emulator) ---
# 로컬 Docker 에뮬레이터 접속용 주소와 가짜 마스터 키
COSMOS_ENDPOINT=https://localhost:8081
COSMOS_KEY=C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==
COSMOS_DATABASE=LogDoctorDB
AZURE_COSMOS_EMULATOR_IP_ADDRESS_OVERRIDE=127.0.0.1
```

---

## 💡 최종 동작 원리 (요약)

1. **프론트엔드**는 `AAD_APP_...` 변수들을 쳐다보고 "나 M365 유저(chjcmy)인데 통과시켜줘!" 라고 토큰을 받아냅니다.
2. **백엔드**는 `CLIENT_ID`와 `TENANT_ID`를 쳐다보고 "프론트엔드가 가져온 토큰 주인이 맞네, 인정!" (검증 통과).
3. **백엔드가 Azure 구독을 조회할 때**는 프론트엔드 토큰을 쓰레기통에 버리고(`AUTH_METHOD=managed_identity`), 질문자님이 터미널에서 `azd auth login`으로 접속해 둔 **개인 계정(chjcmy@gmail.com, Azure for Students의 주인)** 의 막강한 권한 무기를 꺼내서 Azure 성벽(MFA)을 완벽하게 부수고 들어갑니다.
