# Mission Briefing: Log Doctor Azure Agent Implementation

이 문서는 **Log Doctor 공급자 백엔드(Provider Backend)**와 통신하며 고객사 환경을 분석할 **에이전트(Azure Functions - Python)** 구현을 위한 기술 가이드입니다.

## 1. 개요 (Context)

공급자 백엔드는 모든 에이전트의 코드와 정책을 중앙 제어하는 허브 역할을 합니다. 에이전트는 고객사 Azure 환경에 설치되지만, 실행 코드는 공급자로부터 매번 내려받고(Streaming), 실행 흐름은 폴링(Polling)을 통해 지시받습니다.

## 2. 핵심 구현 사항 (Technical Requirements)

### 2.1. 인증 및 보안 (Authentication)

- **대상**: 모든 공급자 백엔드 API 호출.
- **방식**: Azure Managed Identity (System-assigned)를 사용한 Bearer 토큰 인증.
- **헤더**: `Authorization: Bearer <ID_TOKEN>`
- **주의**: 공급자 백엔드는 이 토큰을 검증하여 테넌트 위계(`tenant_id`)를 확인합니다.

### 2.2. 핸드쉐이크 (Passive Handshake)

- **목적**: 설치 직후 또는 구동 시 에이전트의 존재를 등록.
- **Endpoint**: `POST {PROVIDER_URL}/api/v1/agents/handshake`
- **Body**:
  ```json
  {
    "tenant_id": "...",
    "subscription_id": "...",
    "agent_version": "...",
    "capabilities": ["detect", "filter"]
  }
  ```

### 2.3. 폴링 로직 (Control Loop)

- **목적**: 분석 트리거 여부 및 최신 설정 확인.
- **Endpoint**: `GET {PROVIDER_URL}/api/v1/agents/should-i-run?tenant_id=...&agent_id=...`
- **주기**: `TimerTrigger` (예: 1분 간격) 또는 `QueueTrigger`.

### 2.4. 패키지 다운로드 & 업데이트 (Download & Update)

- **목적**: 에이전트 소스 원본 Zip 획득 및 최신 버전 체크.
- **Endpoint**: `GET {PROVIDER_URL}/api/v1/packages/download?version=latest&token={DOWNLOAD_TOKEN}`
- **보안 사항**:
  - `User-Agent` 필수: 브라우저가 아닌 에이전트 식별자(예: `Log-Doctor-Agent`)를 포함해야 함.
  - `token`: 템플릿 배포 시 주입된 전용 JWT 토큰 사용.

## 3. 배포 아키텍처 (Deployment)

- **Run From Package**: 에이전트는 소스 코드를 로컬에 저장하지 않습니다.
- **Source**: `WEBSITE_RUN_FROM_PACKAGE = {PROVIDER_URL}/api/v1/packages/download?version=latest&token=...`
- 이 설정은 인프라 설치 시점(Bicep)에 공급자 백엔드가 최신 Zip 파일 경로를 계산하여 주입해 줍니다.

## 4. 구현 가이드라인

- **언어**: Python 3.11+
- **패키징**: `func archive` 형태의 Zip 배포.
- **복원력**: 공급자 백엔드 일시 장애 시 지수 백오프(Exponential Backoff)를 적용한 재시도 로직 필수.

---

**공급자 백엔드 현재 상태**:

- `/api/v1/packages/download` (토큰 기반 스트리밍 완료)
- `/api/v1/agents/handshake` (Identity 기반 등록 완료)
- `/api/v1/subscriptions/setup-info` (Bicep 파라미터 주입 로직 완료)
- **보안 가드**: 모든 다운로드 요청에는 `@download_token_required` AOP 가드가 적용되어 있습니다.
