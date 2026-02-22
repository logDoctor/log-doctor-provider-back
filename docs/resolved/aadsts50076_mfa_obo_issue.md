# 장애 원인 분석 및 해결 가이드: Azure AD OBO 흐름과 MFA 인증 충돌 (AADSTS50076)

- **발생일자:** 2026-02-21
- **관련 기술 트리:** Azure Active Directory, MSAL, On-Behalf-Of (OBO) Flow, Azure CLI, DefaultAzureCredential

---

## 🛑 1. 문제 발생 개요 (Context)

Teams 앱(프론트엔드)이 성공적으로 SSO 토큰을 받아 백엔드로 전달했고, 백엔드는 이 클라이언트 토큰을 사용해 사용자를 대신하여(On-Behalf-Of) Azure Resource Management API를 호출해 사용자별 **구독(Subscription) 목록**을 불러오려고 시도했습니다. 하지만 아래와 같은 Azure AD 통신 에러가 지속적으로 발생했습니다.

### 발견된 대표 에러 로그
1. **AADSTS50076**: `... you must use multi-factor authentication to access '797f4846-ba00-4fd7-ba43-dac1f8f63013'.`
2. **AADSTS7000219**: `'client_assertion' or 'client_secret' is required...`
3. **AADSTS500011**: `The resource principal named ... was not found in the tenant named 기본 디렉터리.`

---

## 🔍 2. 근본적인 원인 분석 (Root Causes)

이 문제는 크게 두 가지가 동시에 얽힌 치명적인 **"인증 구조적 한계 + 계정의 파편화"** 문제였습니다.

### 원인 1: OBO (On-Behalf-Of) 흐름의 MFA(2단계 인증) 한계
- Azure 리소스 관리 API(`797f4846...`)는 보안상 무조건 **MFA 인증을 거친 토큰**만을 받습니다. 
- 하지만 프론트엔드가 건네준 SSO 토큰에는 MFA 검사가 수행되었다는(보안 도장) 증명이 누락되어 있었습니다. 
- 이 토큰을 교환(OBO)하는 백엔드 서버(API) 입장에서는 팝업창을 띄워 사용자에게 휴대폰 승인을 요청할 수 있는 **UI 제어 능력이 없기 때문에 시스템이 멈춰버렸습니다.**

### 원인 2: 프론트엔드 환경(M365)과 백엔드 자원(Azure) 계정의 파편화
- 프론트엔드 Teams 로그인 계정: `chjcmy@logdoctor.onmicrosoft.com` (Teams 앱 개발용)
- 백엔드 OBO 타겟 리소스(Azure for Students): `3sesac44@aisesac.onmicrosoft.com` (Azure 자원용)
- OBO 로직은 '넘어온 토큰의 주인(chjcmy) 행세'를 그대로 하기 때문에, MFA를 기적적으로 뚫었다 해도 이 계정 소유의 구독은 없으므로 에러가 나거나 텅 빈 결과를 냈을 것입니다.

---

## 🛠️ 3. 해결 과정 및 아키텍처 개선 (Resolution)

이 문제를 우회하고 완벽에 가까운 로컬 테스트 환경을 구축하기 위해 아키텍처를 변경했습니다. 결론적으로, **"남의 토큰으로 교환받는 불완전한 OBO"**를 로컬 환경에서는 버리고, **"방금 직접 인증한 내 확실한 개발자 권한 인증서"**를 직접 사용하도록 수정했습니다.

### 수정 1단계: 프론트엔드 프로비저닝 복원
- 복잡하게 얽힌 회사 권한 문제를 우회하고자, Teams Toolkit이 생성한 내 권한 100% 로컬 무료 앱(`logdoctorlocal`)으로 `.env.local` 및 백엔드 `.env`의 클라이언트 ID를 원상 복구했습니다.

### 수정 2단계: 백엔드 `auth_provider.py` 인증 파이프라인 전면 개편
- `AUTH_METHOD=managed_identity` 모드일 때, 파워셸이나 CLI에 이미 2단계 인증까지 클리어된 채 저장된 로컬 계정 정보(`DefaultAzureCredential`)를 불러오도록 파이썬 코드를 뜯어고쳤습니다.
  - 관련 모듈: `from azure.identity.aio import DefaultAzureCredential`
  - 에러 해결을 위해 비동기 라이브러리인 `aiohttp`를 `uv pip install aiohttp`로 수동 설치했습니다.

```python
# 기존 OBO 로직 (MFA/테넌트 차이 문제로 터짐)
result = app.acquire_token_on_behalf_of(user_assertion=sso_token, scopes=scopes)

# => 개선된 DefaultAzureCredential 로직 (MFA 인증 및 다중 테넌트 계정 대응)
if settings.AUTH_METHOD == "managed_identity":
    credential = DefaultAzureCredential()
    token_info = await credential.get_token("https://management.azure.com/.default")
    await credential.close()
    return token_info.token
```

### 수정 3단계: 터미널 수동 로그인 (Azure Developer CLI)
- 여전히 백엔드(DefaultAzureCredential)가 엉뚱한 테넌트(`기본 디렉터리`)의 토큰을 뒤지는 이슈(`AADSTS500011`)가 터졌습니다.
- 이를 해결하기 위해 터미널에서 프로그래머용 특수 개발 툴 로그인을 수행하여 캐시를 생성하였습니다.
  ```bash
  $ brew install azd          # Azure Developer CLI 설치
  $ azd auth login            # 브라우저 창에서 내 진짜 Azure 계정(3sesac44)으로 로그인 (MFA 포함)
  ```
- OBO 코드에 강제로 `tenant_id`를 하드코딩하지 않고, `DefaultAzureCredential()`이 방금 `azd`로 저장해 둔 `3sesac44` 계정을 완벽하게 자동으로 찾아내도록(Fallback) 만들었습니다.

---

## 🎓 4. 학습 포인트 (Takeaways)

1. **사용자 UI가 없는 서버 투 서버 (Backend to Backend) 통신(App Service 등)에서는** 사용자에게 팝업을 요구하는 MFA 정책이 심각한 통신 블로커(Blocker)가 됩니다.
2. 해결책으론 **사용자 토큰 위임(OBO) 대신, 시스템 자체가 가진 권한(Managed Identity, Service Principal)** 을 사용하면 복잡한 개인 사용자 인증 절차를 우회하고 데이터에 접근할 수 있습니다.
3. Microsoft 클라우드 기술(Teams M365 + Azure)을 동시에 사용할 때는 **Teams/Office 개발 테넌트 계정과 Azure 과금 테넌트 계정이 다르기 쉬우므로, 자격을 분리해서 테스트하는 파이프라인의 설계**가 필수적입니다.
