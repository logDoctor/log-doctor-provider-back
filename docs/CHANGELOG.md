# CHANGELOG

## 2026-04-29

### 정기 검진 (Scheduled Diagnosis) 기능 추가

1. **Schedule 도메인 신설** — Agent aggregate 하위에 `Schedule` 엔티티 및 레포지토리 추가 (`app/domains/agent/models/schedule.py`, `app/domains/agent/schedule_repository.py`).
2. **`POST /agents/{agent_id}/trigger-scheduled-run`** — 에이전트 타이머 폴링용 엔드포인트 신설. ETag 낙관적 잠금으로 다중 레플리카 중복 실행 방지.
3. **Schedule CRUD 엔드포인트** — `GET/POST /agents/{agent_id}/schedules`, `PATCH/DELETE /agents/{agent_id}/schedules/{id}` (운영자 전용).
4. **ETag 잠금 → Report 생성 → Queue push** 순서로 트랜잭션 설계 (R1: 중복 실행 방지 > 누락 허용).
5. **알림 분기** — `triggered_by.startswith("scheduled:")` 시 "⏰ 정기 검진 완료" 타이틀 적용 (`notification/service.py`).
6. **ROUTINE/MANUAL 필터 수정** — `triggered_by = "scheduled:{id}"`를 ROUTINE으로 분류 (`report/repository.py`).
7. **에이전트 삭제 cleanup** — `DeactivateAgentUseCase`, `ConfirmAgentDeletionUseCase`, `TenantAdminUninstallUseCase` 에서 연관 스케줄 `disable_by_agent()` 호출.
8. **`schedules` Cosmos 컨테이너 추가** — `scripts/setup_db.py` 업데이트.
9. **아키텍처 문서** — `docs/scheduled-diagnosis-architecture.md` 작성.

---

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
