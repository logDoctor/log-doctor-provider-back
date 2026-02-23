# Troubleshooting: Azure Entra ID Authentication (AADSTS700054)

Azure Container Apps(ACA) 배포 후 `/docs` 등 인증이 필요한 페이지에 접속할 때 발생하는 `AADSTS700054` 에러에 대한 해결 방법입니다.

## 1. 에러 증상 (Symptoms)

- 로그인을 시도하면 다음과 같은 메시지가 나타남:
  > `AADSTS700054: response_type 'id_token' is not enabled for the application.`

## 2. 발생 원인 (Cause)

- Azure Container Apps의 내장 인증(EasyAuth)은 로그인 과정에서 `id_token`을 요청합니다.
- 보안을 위해 최신 Azure Entra ID(AD) 앱 등록에서는 '암시적 흐름(Implicit Grant)'을 통한 토큰 발급이 기본적으로 비활성화되어 있습니다.

## 3. 해결 방법 (Solution)

### Step 1: ID 토큰 발급 활성화

1. [Azure Portal](https://portal.azure.com) 접속 > **App registrations (앱 등록)** 선택
2. 해당 애플리케이션 선택 > **Authentication (인증)** 메뉴로 이동
3. 상단 탭에서 **설정 (Settings)** 클릭
4. **Implicit grant and hybrid flows (암시적 허용 및 하이브리드 흐름)** 섹션에서 **ID tokens (used for implicit and hybrid flows)** 체크박스에 체크
5. 상단 **Save (저장)** 버튼 클릭

### Step 2: 플랫폼 설정 확인 (Web vs SPA)

ACA의 런인 인증을 사용할 경우, 플랫폼 유형이 `Single-page application (SPA)`이 아닌 **`Web`**으로 설정되어 있어야 에러가 재발하지 않습니다.

1. **Authentication (인증)** 메뉴 > **리디렉션 URI 구성** 탭
2. **리디렉션 URI 추가** 클릭 > **웹 (Web)** 플랫폼 선택
3. 다음 형식의 URI를 입력: `https://<당신의-ACA-주소>/.auth/login/aad/callback`
4. 저장

## 4. 참고 사항

- 설정 변경 후 반영까지 약 1~2분의 시간이 소요될 수 있습니다.
- 브라우저 쿠키 문제로 인해 설정 변경 후에도 동일 에러가 난다면, 시크릿 모드(Incognito)에서 다시 시도해 보세요.
