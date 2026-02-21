q# CHANGELOG

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

## 2026-02-20

### sunghean

1. 로컬 개발용 Azure Cosmos DB Emulator(`localhost:8081`) 접속을 위해 `.env` 템플릿 업데이트 및 `COSMOS_KEY` 변수 도입.
2. `app/infra/db/cosmos.py`에서 로컬 환경 시 Entra ID(`DefaultAzureCredential`) 대신 Primary Key 인증 방식을 자동 사용하도록 호환성 패치 적용.

## 2026-02-21

### Choe Seonghyeon

1. 로컬 환경에서 Azure Cosmos DB Emulator 구동 및 백엔드 연결 안정화.
   - `docker-compose.yml` 리소스에 에뮬레이터 IP 라우팅 문제 해결을 위한 `AZURE_COSMOS_EMULATOR_IP_ADDRESS_OVERRIDE` 환경 변수 추가.
   - 백엔드 컨테이너의 로컬 DB 인증을 위해 `COSMOS_KEY` 고정 변수 주입 추가.
   - `app/infra/db/cosmos.py`에서 `enable_endpoint_discovery=False` 옵션을 추가하여 Docker 내부 컨테이너 통신 시 발생하는 127.0.0.1 라우팅(Connection Refused) 에러 해결.
2. 로컬 개발 환경용 Azure AD 인증 처리 방식 전면 수정 (`AADSTS50076` MFA 에러 해결).
   - `app/core/auth_provider.py`에서 로컬 `AUTH_METHOD`가 `managed_identity`일 경우 OBO(On-Behalf-Of) 토큰 교환을 생략하고 `azure-identity` 패키지의 `DefaultAzureCredential`을 사용하여 직접 토큰 발급.
   - 이를 통해 프론트엔드 토큰(Microsoft 365 계정)과 백엔드 토큰(Azure 계정) 분리 상황에서 발생하는 Tenant 불일치 및 MFA 요구 에러 방지.
   - `aiohttp` 패키지 추가를 통한 로컬 비동기 인증 파이프라인 수립.
3. Python 버전 고정 및 패키지 환경 동기화 (`uv`).
   - `uv`를 이용하여 백엔드 런타임을 Python 3.12로 고정(`.python-version` 추가).
   - 클라우드 배포 호환성을 위해 `uv.lock` 및 `requirements.txt` 최신화 및 안쓰는 패키지 정리.
