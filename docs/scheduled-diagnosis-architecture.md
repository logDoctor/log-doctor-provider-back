# 정기 검진 (Scheduled Diagnosis) 아키텍처

## 개요

온디맨드 진단(사용자가 버튼을 눌러 실행)에 더해, 관리자가 설정한 스케줄(매일/매주/매월 등)에 따라 자동으로 정기 진단이 실행됩니다.

## 아키텍처 선택: Pull-based 폴링

### 왜 Push 방식이 아닌가?

Provider-back은 ACA(Azure Container Apps) Serverless로 배포됩니다. `minReplicas`가 설정되지 않으면 scale-to-zero 되므로 `lifespan` 백그라운드 태스크(APScheduler 등)에 의존할 수 없습니다.

### Pull-based 선택 이유

- **Client-back(Azure Functions)**의 타이머 트리거는 Consumption plan에서도 항상 실행됩니다.
- 에이전트 타이머가 30분마다 provider에 `POST /agents/{id}/trigger-scheduled-run`을 호출합니다.
- Provider는 스케줄을 확인하고 실행 여부를 결정합니다.

## 전체 데이터 흐름

```
Azure Functions (client-back)          ACA Provider (scale-to-zero OK)
─────────────────────────────          ──────────────────────────────
[Timer - 30분마다 자동 wake-up]
         │  0~3분 무작위 jitter (thundering herd 방지)
         │
         │  POST /api/v1/agents/{agent_id}/trigger-scheduled-run
         │  ?tenant_id={tenant_id}
         ├──────────────────────────────────────────→
         │                                     Schedule 조회
         │                                     CronHelper.is_time_to_run()
         │                                          ↓ due인 경우만
         │                                     Schedule ETag 업데이트 (잠금)
         │                                     Report.create() → Cosmos
         │                                     Queue push (에이전트 큐)
         │                                     next_run_at 업데이트
         │  ← {triggered: true, report_id: "실제-UUID", configurations: [...]}
         │
[orchestration 시작 - 실제 report_id 사용]
         ↓
기존 orchestrator → activities → update_status_activity
(PATCH /reports/{실제 report_id} → 404 없음)
         ↓
NotificationService → "⏰ 정기 검진 완료" Teams 알림
```

## GET → POST 변경 이유

기존 `GET /should-i-run`은 Report 생성 + Queue push라는 사이드이펙트가 있는 GET이었습니다.
재시도 시 중복 실행 위험이 있어 `POST /trigger-scheduled-run`으로 변경했습니다.

## Schedule 엔티티

`Schedule`은 **Agent aggregate의 하위 개념**입니다. 독립적인 생명주기가 없으며, Agent 없이 존재할 수 없습니다.

```python
@dataclass
class Schedule:
    id: str
    tenant_id: str          # Cosmos partition key
    agent_id: str
    enabled: bool
    cron_expression: str    # 5-field: "0 9 * * 1"
    timezone: str           # IANA: "Asia/Seoul"
    language: str           # "ko" | "en"
    configurations: list[dict]   # DiagnosticRuleConfiguration 스냅샷
    last_run_at: str | None
    next_run_at: str | None
    _etag: str | None       # 낙관적 잠금용
```

**Cosmos 컨테이너:** `schedules` (partition key: `/tenant_id`)

**REST 경로:** `/v1/agents/{agent_id}/schedules` (Agent sub-resource)

## TriggerScheduledRunUseCase 연산 순서 (R1 설계 결정)

여러 단계에서 각각 실패할 수 있으므로 "실패 방향"을 결정했습니다.

**선택: 중복 실행 방지 > 누락 허용**

```
1. Schedule ETag 업데이트 (last_run_at, next_run_at)
   └─ CosmosAccessConditionFailedError → 다른 레플리카가 선점 → triggered: false 반환

2. Report.create() → Cosmos 저장
   └─ 실패 시 → 이 사이클 누락 허용
      (스케줄 잠금은 이미 업데이트됨 → 다음 주기에 재시도 안 됨)

3. Queue push
   └─ 실패 시 → Report.mark_as_failed() 저장 (기존 패턴과 동일)
```

**이유:** 정기 검진 1회 누락 < 동일 진단 2회 중복 실행 (과금, 알림 오발송).

## ETag 낙관적 잠금 동작 방식

ACA가 다중 레플리카로 실행될 때, 동일 스케줄에 대해 여러 레플리카가 동시에 `trigger-scheduled-run`을 처리할 수 있습니다.

1. 첫 번째 레플리카가 `schedule._etag`를 포함하여 `replace_item()` 호출
2. 성공 → 해당 레플리카가 Report 생성 및 Queue push 진행
3. 두 번째 레플리카가 동일 ETag로 `replace_item()` 호출 → `CosmosAccessConditionFailedError`
4. 두 번째 레플리카는 `continue`로 스킵 → `triggered: false` 반환

## `triggered_by` 필드 규약

| 값 | 의미 |
|---|---|
| `null` / `"System"` | 시스템 또는 정기 진단 (구버전) |
| `"scheduled:{schedule_id}"` | 정기 검진 스케줄 자동 실행 |
| 이메일 주소 | 사용자 온디맨드 실행 |

Report 조회 시 `diagnosis_type` 필터:
- `ROUTINE`: `triggered_by`가 없거나 `"System"` 또는 `"scheduled:"` prefix
- `MANUAL`: `triggered_by`가 있고 `"System"` 또는 `"scheduled:"` prefix가 아닌 경우

## 에이전트 삭제 시 스케줄 cleanup

에이전트 삭제/비활성화 시 연관 스케줄을 `enabled=false`로 처리합니다 (하드 삭제 대신 감사 추적 유지).

대상 유스케이스:
- `DeactivateAgentUseCase` → `schedule_repository.disable_by_agent()`
- `ConfirmAgentDeletionUseCase` → `schedule_repository.disable_by_agent()`
- `TenantAdminUninstallUseCase` → 각 에이전트마다 `schedule_repository.disable_by_agent()`

## 과금 정책

- 에이전트당 기본 1개 무료 (`FREE_SCHEDULE_LIMIT = 1`)
- 초과 시 `ForbiddenException` (향후 유료 플랜 연동)
- 스케줄 생성 시 한도 체크; 실행 시에는 체크 안 함 (기존 스케줄은 grandfathered)

## Thundering Herd 방지 (R4)

타이머가 `run_on_startup=True`이므로 여러 에이전트 인스턴스가 동시에 배포될 경우 동시 폴링 폭주가 발생할 수 있습니다.

`timer.py`에서 0~3분 무작위 jitter를 적용합니다:
```python
jitter_seconds = random.uniform(0, 180)
await asyncio.sleep(jitter_seconds)
```
에이전트 100개 기준: 평균 0.5초 간격 분산 → provider 부하 없음.
