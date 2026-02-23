# 클라이언트 에이전트 자동 배포 파이프라인 (Token-Based Automated Download Pipeline)

본 문서는 Log Doctor 시스템에서 고객사용 Azure Function(클라이언트 에이전트)이 초기 배포 시 또는 스케일 아웃 시점에 Provider 측 백엔드로부터 안전하게 에이전트 실행 코드를 자동 다운로드받는 파이프라인의 아키텍처 및 구현 세부사항을 정리합니다.

## 1. 목적 (Goal)

과거에는 클라이언트가 GitHub Release나 외부 공용 Blob URL을 통해 에이전트 코드를 받아야 했으나, 이는 외부 저장소 의존성이 크고 보안 관리가 어려웠습니다. 이를 개선하여 **Provider 백엔드가 주체가 되어 스스로 최신의 에이전트 코드를 서빙**하되, **인가되지 않은 사용자의 무단 소스코드 열람을 차단**하는 안전한 파이프라인을 구축했습니다.

## 2. 주요 아키텍처 및 기술 (Key Architecture & Technologies)

추가적인 DB 접근이나 상태 관리 없는 **Stateless 보안**과 클라우드 배포 엔진의 특수성을 고려한 **AOP(관점 지향 프로그래밍)** 기반 보안 계층을 설계했습니다.

- `app/api/v1/endpoints/template.py`: 템플릿 생성 시 다운로드용 JWT 발급
- `app/domains/package/router.py`: 패키지 서빙 Usecase 호출 라우터
- `app/core/auth/guards/download_guard.py`: AOP 기반다운로드 전용 보안 검증 (Decorator)
- `app/domains/package/usecases/download_package_use_case.py`: 내부 버전 처리 및 Payload 스트리밍 구현

## 3. 작동 흐름 (Data Flow)

안전한 패키지 스트리밍은 다음의 6단계를 거쳐 이루어집니다.

1.  **비밀 키(Secret Key) 조달**: 인프라 배포 리소스(`aca.bicep`)를 통해 `DOWNLOAD_SECRET_KEY`가 해당 Provider 환경에 유일(Unique)한 해시값으로 런타임에 동적 주입됩니다.
2.  **템플릿에 URL 및 Token 주입**: 고객사가 `[Admin UI]`에서 "설치 템플릿"을 요청하면, 백엔드는 즉석에서 `DOWNLOAD_SECRET_KEY`로 무기한 토큰(JWT)을 서명 발급하여 Azure Function의 `WEBSITE_RUN_FROM_PACKAGE` 환경 변수에 주입합니다.
    - _예시 URL:_ `https://[provider-url]/api/v1/packages/download?version=latest&token=ey...`
3.  **App Service 엔진 구동**: 고객이 배포 템플릿 버튼을 클릭하면, Azure의 App Service 배포 엔진 빈 껍데기의 Function 앱을 올리면서 위 URL로 HTTP 다운로드 요청을 트리거합니다.
4.  **AOP 기반 방어막 (Guard) 통과**: 백엔드 라우터 도달 전 `@download_token_required` 가드가 요청을 가로챕니다.
    - `User-Agent` 검사: 해커가 토큰을 탈취해 웹 브라우저 (Chrome, Safari 등)에서 URL을 붙여넣기하는 시도를 원천 차단합니다.
    - `Token` 검증: 서명 해시를 이용해 위변조 여부를 재빠르게 판단합니다.
5.  **버전 결정 (UseCase 위임)**: 사용하지 않는 비즈니스 로직을 라우터 컨트롤러에서 모두 끌어내어 단일하게 책임을 지워둔 `DownloadPackageUseCase`를 실행합니다.
6.  **Blob Storage 스트리밍**: Usecase는 최종적으로 Azure Blob Storage에서 Zip 파일 스트림을 열어 고객 클라이언트로 즉시 반환하여 배포를 완료시킵니다.

## 4. 보안적 의의 (Security Implications)

가장 큰 특징은 기존 관리자(Operator)가 쓰던 Entra ID(OIDC) 인증 절차와 이번 다운로드 파이프라인의 인증 절차를 **물리적으로 이원화** 했다는 점에 있습니다.

- **엔진 vs 휴먼 구분 지향**: 템플릿의 `WEBSITE_RUN_FROM_PACKAGE` 작동 방식상 주체가 '사람'이 아닌 '애저 내부의 자동 엔진(익명)'이 되므로, 이에 적합한 전용 가벼운 증명 모델(Token + UserAgent)을 도입했습니다.
- **영구 토큰의 안정성 선택**: Azure Function의 극단적인 특성(컨테이너가 Restart 되거나, 트래픽 폭주 시 인스턴스가 늘어날 때마다 패키지 원본 URL에 재접근) 상, 토큰 1회 만료/시간 만료 제약을 걸어버리면 앱 구동 안정성이 심하게 훼손됩니다.
- **리스크 수용성 (Risk Assessment)**: 해당 URL이 유출되었을 경우를 상정한 워스트 시나리오라도, 고객의 데이터나 키 유출이 아닌 '껍데기 에이전트 소스코드 열람'에 그치도록 설계되었으며 그마저도 브라우저 직접 접근 방지 로직(Guard)을 덧대어 실질적 보안 맹점을 메웠습니다.

### 🔒 향후 보안 고도화 계획 (Source Code Obfuscation)

현재 체계에서도 자격 증명(Secret)은 철저히 보호되지만, Provider의 고도화된 탐지 엔진 로직(IP/비즈니스 로직)이 파이썬 소스 코드(.py) 형태로 B2B 고객사 인프라에 직접 노출되는 문제가 존재합니다.
이를 해결하여 핵심 지적재산을 완벽히 은닉하기 위해, 향후 **에이전트 패키지 CI/CD 빌드 파이프라인(GitHub Actions)에 난독화(Obfuscation) 단계를 통합할 예정**입니다.

**[적용 예정 기술: PyArmor]**

- **개념**: 파이썬 코드를 바이트 코드로 암호화하여 사람이 읽을 수 없고 리버스 엔지니어링이 불가능한 형태로 변환.
- **파이프라인 적용 지점**: 클라이언트 에이전트 소스코드를 `zip`으로 압축하기 직전, `pyarmor gen app/engines/` 명령어를 통해 엔진 관련 폴더만 강제 난독화 처리.
- **효과**: 고객사에서 패키지를 다운로드하거나 Azure Kudu를 통해 파일에 접근하더라도, 엔진 내용은 외계어(암호화 텍스트)로만 보이게 되므로 B2B 신뢰성을 잃지 않으면서도 핵심 기술의 유출을 완벽하게 차단할 수 있습니다.

## 5. 결론

"어떻게 하면 외부 의존성(Public GitHub URL)을 끊고 Provider 내부에서 서빙하면서, 로그인하지 않은 Azure 배포 엔진에도 안전하게 패키지를 제공할까?"라는 핵심 과제에 대해, **AOP를 통한 견고한 아키텍처와 경량화된 JWT Stateless 모델**로 가장 이상적인 답안을 완성했습니다.
