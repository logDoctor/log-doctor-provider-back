# CHANGELOG

## 2026-02-17

### Yoonsik-Shin

1. 저장 시 Prettier 자동 포맷을 활성화하고 VS Code 기본 포맷터로 설정.
2. Python 버전 업그레이드 (3.11 -> 3.12) 및 `uv` 환경 동기화.
3. 전역 예외 처리(Global Exception Handling) 도입 및 커스텀 예외 클래스 정의.
4. CORS 설정 및 보안 미들웨어(TrustedHost, GZip) 적용.
5. `structlog` 기반의 구조화된 로깅 설정 (운영 JSON, 개발 Console).
6. 헬스 체크 엔드포인트(`live`, `ready`) 추가.
7. Docker 및 Docker Compose 설정 (Backend + Azure Cosmos DB Emulator).
8. Azure Container Apps(ACA) 배포 가이드(`docs/aca-guide.md`) 작성.
9. 전체 코드베이스 주석 및 독스트링 한글화.
10. `app/core`, `app/infra/db` 등에 `__init__.py` 단축 임포트(Shortcut) 적용.
11. 프로젝트 이름을 `log-doctor-back`에서 `log-doctor-provider-back`으로 전면 변경.
12. Ruff 도입 (Linting & Formatting) 및 `pyproject.toml` 설정.
13. `docs/CHANGELOG.md` 기록 규칙 수립 및 AI 지침 반영 (English).
14. `app/infra/db/cosmos.py` 및 `app/main.py`에 Graceful Shutdown (DB close) 로직 추가.
15. `tests/__init__.py` 삭제 및 `app/` 하위 패키지 구조 표준화.
16. `pre-commit` 훅 도입으로 커밋 시 자동 포매팅 & 린트 검사 환경 구축.

## 2026-02-22

### Louishstyle

1. 백엔드 Azure Cosmos DB 비동기(AIO) 클라이언트 엔진 구축. (aiohttp 패키지 추가)
2. Domain 계층 NounVerber 네이밍 규칙(TenantOnboarder 등) 전면 적용.
3. Azure Managed Identity(RBAC) 기반의 실제 DB 연동 및 온보딩 핸드셰이크 구현 완료.
4. Repository 인터페이스(ABC)와 Cosmos DB 구현체 분리를 통한 클린 아키텍처 구조 확립.
5. 에이전트 도메인 요청/응답 스키마(AgentHandshakeRequest, AgentHandshakeResponse) 정의 및 Pydantic 기반 유효성 검사 적용.
6. AgentRepository 추상 인터페이스 및 Cosmos DB 기반 비동기 구현체(CosmosAgentRepository) 구현.
7. 에이전트 등록, 테넌트 존재 여부 검증 및 테넌트 상태 활성화를 수행하는 AgentHandshaker 유즈케이스 구현.
8. TenantRepository에 테넌트 개별 조회(get_by_id) 및 데이터 업데이트(update) 메서드 추가하여 도메인 간 교차 로직 지원.
9. FastAPI CBV(Class-Based View) 패턴을 적용한 에이전트 핸드셰이크 API 엔드포인트(/agents/handshake) 개통.
10. dependencies.py를 구축하여 도메인별 리포지토리 및 유즈케이스의 의존성 주입(DI) 흐름 중앙 집중화.
11. 전역 API 라우터(v1_router)에 에이전트 도메인 라우터를 통합하여 외부 API 노출.
12. 커스텀 예외 클래스(LogDoctorException)와 API 응답 구조를 연동하여 에이전트 핸드셰이크 실패 시의 에러 핸들링 강화.
