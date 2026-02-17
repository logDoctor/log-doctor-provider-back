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
