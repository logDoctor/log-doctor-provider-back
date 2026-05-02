# 인사이트 통계 시스템 설계 문서

> **상태**: 설계 완료 / 구현 대기  
> **작성일**: 2026-05-02  
> **관련 코드**: `app/domains/insight/`

## 1. 개요

### 1.1 목적

대시보드의 인사이트 섹션(헬스 스코어, 활성 리스크, 트렌드 차트, 엔진별 분포)의 통계 데이터를
**사전 계산(Pre-computed)** 하여 별도 컨테이너에 저장하고 API로 즉시 제공하는 시스템입니다.

### 1.2 현재 문제

- 프론트엔드에서 reports 목록(최대 20건)을 받아 클라이언트에서 실시간 집계
- 리포트 증가 시 API 응답 크기와 프론트엔드 연산 부하 증가
- 장기간 통계가 부정확 (20건 제한)

### 1.3 해결 방안

- 리포트 완료 / 진단 해결 시 **이벤트 발행 → Queue → 워커가 증분 업데이트**
- 4개 기간별 CosmosDB 컨테이너에 사전 계산된 통계 저장
- 대시보드 조회 시 단일 Point Read로 즉시 반환

---

## 2. 아키텍처

### 2.1 전체 흐름

```
[리포트 완료 / 진단 해결]
    ↓ (이벤트 발행)
[Azure Storage Queue: insight-events]
    ↓ (Background Worker 폴링)
[증분 업데이트 로직]
    ↓ (upsert)
[CosmosDB: insights_daily / insights_weekly / insights_monthly / insights_total]
    ↑ (Point Read)
[GET /api/v1/insights?agent_id=xxx&period=1w]
```

### 2.2 설계 원칙

1. **이벤트 드리븐**: Cron 배치 없이 리포트 완료/진단 해결 시점에 즉시 처리
2. **증분 업데이트**: 전체 재계산 대신 기존 값에 신규 데이터 반영
3. **원본 기준 재계산**: 인사이트를 직접 increment/decrement하지 않고 리포트의 현재 summary를 기준으로 계산 (멱등성 보장)
4. **Queue 직렬화**: Race condition 방지 — 동일 에이전트에 대한 이벤트가 순차 처리됨
5. **3단계 정합성 보정**: Queue 재시도 → Daily Health Check → Admin 재빌드

---

## 3. 기간 정의

### 3.1 달력 기준 (Primary)

모든 기간은 **한국 표준시(KST, Asia/Seoul)** 달력 기준으로 고정됩니다.

| 기간 | UI 라벨 | 경계 | 문서 키 형식 | 예시 (2026-05-02 금) |
|------|---------|------|-------------|---------------------|
| 1D | 1일 | 오늘 00:00 ~ 23:59 KST | `YYYY-MM-DD` | `2026-05-02` |
| 1W | 1주 | 이번 주 월~일 | `YYYY-Www` | `2026-W18` (4/28~5/4) |
| 1M | 1월 | 이번 달 1일~말일 | `YYYY-MM` | `2026-05` (5/1~5/31) |
| ALL | 전체 | 에이전트 전체 기간 | `total` | - |

### 3.2 롤링 윈도우 (Secondary, 추후 확장)

- `insights_daily` 컨테이너의 일별 문서를 read-time 집계
- 롤링 7일: 최근 7개 daily 문서 합산 (~7 RU)
- 롤링 30일: 최근 30개 daily 문서 합산 (~30 RU)
- 별도 사전 계산 불필요, API 파라미터(`mode=rolling`)만 추가

---

## 4. 데이터 모델

### 4.1 CosmosDB 컨테이너 구성

| 컨테이너 | Partition Key | Document ID 패턴 | TTL |
|---------|--------------|------------------|-----|
| `insights_daily` | `/tenant_id` | `{agent_id}:{YYYY-MM-DD}` | 90일 |
| `insights_weekly` | `/tenant_id` | `{agent_id}:{YYYY-Www}` | 365일 |
| `insights_monthly` | `/tenant_id` | `{agent_id}:{YYYY-MM}` | 1095일 |
| `insights_total` | `/tenant_id` | `{agent_id}` | 없음 |

### 4.2 문서 구조 (4개 컨테이너 공통)

```json
{
  "id": "agent-uuid:2026-05-02",
  "tenant_id": "tenant-uuid",
  "agent_id": "agent-uuid",
  "period_type": "daily",
  "period_key": "2026-05-02",
  "last_updated_at": "2026-05-02T06:30:00Z",

  "total_reports": 3,
  "total_detected": 12,
  "total_resolved": 9,
  "total_healthy": 8,
  "active_risks_count": 3,

  "trend": [
    { "label": "09:00", "detected": 5, "resolved": 3 },
    { "label": "14:00", "detected": 4, "resolved": 3 },
    { "label": "18:00", "detected": 3, "resolved": 3 }
  ],
  "engine_distribution": [
    { "engine_code": "DET", "count": 5 },
    { "engine_code": "PRV", "count": 3 },
    { "engine_code": "FLT", "count": 2 },
    { "engine_code": "RET", "count": 2 }
  ],

  "latest_report_id": "report-uuid",
  "ttl": 7776000
}
```

**파생 메트릭** (저장하지 않고 API 응답 시 계산):
- `health_score` = `total_resolved / total_detected * 100` (detected=0이면 100)

**trend 그룹 단위**:
- daily → 시간별 | weekly → 일별 | monthly → 일별 | total → 월별

---

## 5. Queue 설계

### 5.1 인프라

- 기존 Provider Storage Account에 `insight-events` Queue 추가
- Poison Queue: `insight-events-poison` (5회 실패 메시지 격리)

### 5.2 메시지 포맷

```json
{
  "event_type": "report_completed",
  "tenant_id": "...",
  "agent_id": "...",
  "report_id": "...",
  "timestamp": "2026-05-02T06:30:00Z"
}
```

```json
{
  "event_type": "diagnosis_resolved",
  "tenant_id": "...",
  "agent_id": "...",
  "report_id": "...",
  "diagnosis_id": "...",
  "is_resolved": true,
  "timestamp": "2026-05-02T06:35:00Z"
}
```

### 5.3 Worker 동작

- FastAPI lifespan에서 `InsightQueueWorker`를 asyncio task로 시작
- 큐를 5초 간격으로 폴링 (메시지 있으면 즉시 처리)
- Visibility timeout: 30초 (처리 실패 시 30초 후 자동 재등장)
- `dequeue_count >= 5`: Poison Queue로 이동

---

## 6. 증분 업데이트 로직

### 6.1 리포트 완료 (`report_completed`)

```
1. report.summary에서 detected_count, resolved_count, healthy_count 추출
2. KST 기준으로 4개 기간 키 계산 (daily, weekly, monthly, total)
3. 각 컨테이너에서 기존 문서 읽기 (없으면 초기값 생성)
4. 누적 메트릭 증분:
   - total_reports += 1
   - total_detected += summary.detected_diagnosis_count
   - total_resolved += summary.resolved_diagnosis_count
   - total_healthy += summary.healthy_diagnosis_count
5. 스냅샷 메트릭 덮어쓰기:
   - active_risks_count = summary.detected - summary.resolved
   - engine_distribution = 최신 리포트 기준 (summary.engine_counts 또는 diagnoses 조회)
6. trend 배열에 데이터 포인트 추가/갱신
7. Upsert (ETag 기반 낙관적 잠금)
```

### 6.2 진단 해결 (`diagnosis_resolved`)

```
1. 해당 report의 현재 summary 조회 (이미 갱신된 resolved_count 반영)
2. 4개 컨테이너에서 기존 문서 읽기
3. 스냅샷 메트릭만 갱신:
   - active_risks_count = report.summary.detected - report.summary.resolved
   - (latest_report_id가 일치하는 경우에만 갱신)
4. 누적 메트릭(total_detected 등)은 건드리지 않음
5. Upsert
```

### 6.3 멱등성 보장

- `report_completed`: `total_reports`에 이미 반영된 리포트인지 확인 가능 (report_id 기반)
- `diagnosis_resolved`: 항상 리포트의 현재 summary 기준으로 덮어쓰기 → 여러 번 처리해도 동일 결과

---

## 7. 진단 해결 반영 — Race Condition 방지

### 7.1 문제 시나리오

사용자가 진단 5건을 빠르게 연속 해결 → 5개 이벤트 동시 발생

### 7.2 해결 전략

1. **Queue 직렬화**: 같은 큐에서 순차 처리되므로 동시 쓰기 없음
2. **리포트 기준 재계산**: 인사이트를 직접 증감하지 않고 리포트 summary의 현재 값 기준
3. **Deduplication**: 짧은 시간 내 동일 report_id에 대한 여러 이벤트는 최종 처리 시 항상 최신 summary 반영 (멱등)
4. **분리된 메트릭 갱신**: 진단 해결 시 `active_risks_count`만 갱신, 누적 통계(`total_detected/resolved`)는 불변

---

## 8. 정합성 보정 체계

### 8.1 Level 1: 실시간 보호

- Queue visibility timeout (30초) → 처리 실패 시 자동 재등장
- Poison Queue → 5회 실패 메시지 격리 + 알림 로깅

### 8.2 Level 2: 주기적 검증 (Daily Health Check)

- 매일 새벽 3시 KST, Background Worker 내 스케줄러로 실행
- `insights_total`의 `total_reports` vs 실제 COMPLETED 리포트 수 비교
- 불일치 발견 시 자동 재빌드 + 경고 로깅

### 8.3 Level 3: 수동 보정 (Admin API)

- `POST /api/v1/insights/rebuild?agent_id={id}`
- 원본(reports/diagnoses)에서 전체 재계산
- 재빌드 전/후 수치 비교 리포트 반환

---

## 9. API 명세

### 9.1 인사이트 조회

```
GET /api/v1/insights?agent_id={agent_id}&period={period}
```

**Query Parameters:**

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `agent_id` | string | ✅ | 에이전트 ID |
| `period` | string | ✅ | `1d`, `1w`, `1m`, `all` |

**Response (200 OK):**

```json
{
  "period": "1w",
  "period_label": "2026년 4월 28일 (월) ~ 5월 4일 (일)",
  "health_score": 95,
  "active_risks_count": 3,
  "total_reports": 12,
  "total_detected": 45,
  "total_resolved": 42,
  "trend": [
    { "label": "4/28 월", "detected": 5, "resolved": 3 },
    { "label": "4/29 화", "detected": 8, "resolved": 7 }
  ],
  "engine_distribution": [
    { "engine_code": "DET", "label": "탐지", "count": 15 },
    { "engine_code": "PRV", "label": "예방", "count": 10 },
    { "engine_code": "FLT", "label": "필터", "count": 12 },
    { "engine_code": "RET", "label": "보존", "count": 8 }
  ],
  "last_updated_at": "2026-05-02T06:00:00Z"
}
```

**Response (404):** 해당 기간 인사이트 없음 → 프론트에서 빈 상태 UI 표시

### 9.2 인사이트 재빌드 (Admin)

```
POST /api/v1/insights/rebuild?agent_id={agent_id}
```

**Response (200 OK):**

```json
{
  "status": "rebuilt",
  "agent_id": "...",
  "containers_updated": ["daily", "weekly", "monthly", "total"],
  "total_reports_processed": 45
}
```

---

## 10. 이벤트 발행 지점

### 10.1 리포트 완료 시

**파일**: `app/domains/report/usecases/update_report_status_use_case.py`

리포트 상태가 COMPLETED로 변경된 후:
```python
await self.insight_publisher.publish({
    "event_type": "report_completed",
    "tenant_id": report.tenant_id,
    "agent_id": report.agent_id,
    "report_id": report.id,
})
```

### 10.2 진단 해결 시

**파일**: `app/domains/report/usecases/update_diagnosis_resolution_use_case.py`

진단 항목의 `is_resolved` 변경 및 리포트 summary 업데이트 후:
```python
await self.insight_publisher.publish({
    "event_type": "diagnosis_resolved",
    "tenant_id": tenant_id,
    "agent_id": report.agent_id,
    "report_id": report.id,
    "diagnosis_id": diagnosis_id,
    "is_resolved": is_resolved,
})
```

---

## 11. 파일 구조

```
app/domains/insight/
├── __init__.py
├── models.py                          # InsightDocument, InsightTrendItem, InsightEngineItem
├── schemas.py                         # InsightResponse, InsightRebuildResponse, InsightEventMessage
├── constants.py                       # PERIOD_TYPES, TTL 설정, KST timezone
├── dependencies.py                    # FastAPI DI 설정
├── router.py                          # GET /insights, POST /insights/rebuild
├── repositories/
│   ├── __init__.py
│   └── insight.py                     # InsightRepository (4개 컨테이너 접근)
├── usecases/
│   ├── __init__.py
│   ├── get_insight_use_case.py        # 조회 (달력 기준)
│   ├── update_insight_use_case.py     # 증분 업데이트 (report_completed)
│   ├── recalculate_metrics_use_case.py # 최신 메트릭 재계산 (diagnosis_resolved)
│   └── rebuild_insight_use_case.py    # 전체 재빌드 (admin/health check)
└── services/
    ├── __init__.py
    ├── insight_event_publisher.py     # Queue에 이벤트 발행
    ├── insight_queue_worker.py        # Queue에서 이벤트 소비 + 처리
    └── insight_health_checker.py      # Daily Health Check 스케줄러
```

---

## 12. IaC 변경 사항

### 12.1 CosmosDB (cosmos.bicep)

4개 인사이트 컨테이너 추가:
```
insights_daily   (PK: /tenant_id, defaultTtl: -1)
insights_weekly  (PK: /tenant_id, defaultTtl: -1)
insights_monthly (PK: /tenant_id, defaultTtl: -1)
insights_total   (PK: /tenant_id, defaultTtl: -1)
```

### 12.2 Storage (storage.bicep)

Queue 서비스 + 2개 큐 추가:
```
insight-events          (메인 큐)
insight-events-poison   (실패 메시지 격리)
```

---

## 13. 구현 단계 (로드맵)

| 단계 | 작업 | 의존성 |
|------|------|--------|
| **1** | IaC: CosmosDB 4개 컨테이너 + Storage Queue 추가 | 없음 |
| **2** | 도메인 모델 + 스키마 + 상수 정의 | 없음 |
| **3** | InsightRepository 구현 (4개 컨테이너 CRUD) | 단계 1, 2 |
| **4** | InsightEventPublisher 구현 (Queue 발행) | 단계 1 |
| **5** | UpdateInsightUseCase 구현 (report_completed 증분) | 단계 2, 3 |
| **6** | RecalculateMetricsUseCase 구현 (diagnosis_resolved) | 단계 2, 3 |
| **7** | InsightQueueWorker 구현 (Queue 소비 + 라우팅) | 단계 4, 5, 6 |
| **8** | main.py lifespan에 Worker 통합 | 단계 7 |
| **9** | GetInsightUseCase + Router 구현 (조회 API) | 단계 3 |
| **10** | 이벤트 트리거 연동 (report/diagnosis UseCase 수정) | 단계 4 |
| **11** | RebuildInsightUseCase + Admin API 구현 | 단계 3 |
| **12** | InsightHealthChecker 구현 (Daily 검증) | 단계 11 |
| **13** | 프론트엔드 연동 (DashboardStats API 전환) | 단계 9 |

---

## 14. 프론트엔드 변경 요약

### 14.1 endpoints.ts

```typescript
INSIGHTS: {
    GET: (agentId: string) => `/v1/insights?agent_id=${agentId}`,
    REBUILD: (agentId: string) => `/v1/insights/rebuild?agent_id=${agentId}`,
},
```

### 14.2 DashboardStats.tsx

- 기존: `reports` prop에서 클라이언트 집계 → 제거
- 변경: `agent_id` + `period` 기반 API 호출
- `range` 탭 변경 시 API 재호출 (`period` 파라미터만 변경)
- `health_score`, `active_risks_count`, `trend`, `engine_distribution` → API 응답에서 직접 사용
- 빈 상태(404): 기존 empty state UI 재활용

---

## 15. 검증 체크리스트

- [ ] 리포트 완료 → Queue 메시지 발행 확인
- [ ] Queue 메시지 → 4개 컨테이너 문서 생성/갱신 확인
- [ ] 진단 해결 → active_risks_count 감소 확인
- [ ] 동시 진단 해결 5건 → race condition 없이 정확한 값
- [ ] 컨테이너 강제 재시작 → 큐 메시지 재처리 확인
- [ ] KST 기간 키 정확성 (일/주/월 경계)
- [ ] 주/월 전환 시 새 문서 자동 생성
- [ ] Daily Health Check → 불일치 감지 및 자동 보정
- [ ] Admin 재빌드 → 전체 재계산 정확성
- [ ] 대시보드 기간 탭 전환 → 올바른 데이터 표시
- [ ] TTL 만료 → 오래된 daily 문서 자동 삭제

---

## 16. 구현 현황 및 미구현 사항 (Implementation Status)

현재 실시간 통계 제공을 위한 핵심 아키텍처는 구축되었으나, 일부 자동화 및 고도화 기능은 향후 과제로 남겨두었습니다.

### ✅ 구현 완료 사항
- **이벤트 기반 실시간 업데이트**: 리포트 완료 및 진단 해결 시 즉시 통계 반영.
- **기간별 다중 컨테이너 저장**: Daily, Weekly, Monthly, Total 사전 집계.
- **고성능 조회 API**: 복잡한 집계 쿼리 없이 Sub-second 대시보드 로딩 보장.
- **수동 정합성 복구 (Level 3)**: `POST /insights/rebuild` API를 통한 전체 재계산 로직.
- **프론트엔드 최적화**: 브라우저 부하를 제거하고 서버 사이드 통계 데이터 연동 완료.

### ⏳ 미구현 사항 (Future Tasks)
1. **자동 정기 정합성 체크 (Level 2)**
   - 매일 특정 시간에 원본 데이터와 통계 데이터를 비교하여 자동으로 오차를 보정하는 스케줄러(Batch) 연동은 미구현 상태입니다. (현재는 수동 API로만 가능)
2. **실제 비용 절감액(Estimated Savings) 계산 로직**
   - 현재 대시보드와 백엔드에는 필드만 존재하며, 리소스별 실제 절감 금액을 산출하는 비즈니스 로직은 추후 고도화가 필요합니다.
3. **테넌트 통합 대시보드 API**
   - 개별 에이전트 단위가 아닌 테넌트 전체의 현황을 요약하는 집계 API 및 UI 개발이 필요합니다.
