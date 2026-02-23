# Application Insights 도입 결정

## 배경

Azure Portal에서 Function App의 실행 로그를 확인하려면 별도의 설정이 필요하다.  
Bicep을 통해 인프라를 프로비저닝할 때 이를 함께 구성하는 방안을 검토했다.

---

## 결론

**Application Insights를 `functions.bicep`에 추가한다.**

---

## Azure Portal에서 볼 수 있는 로그

| 로그 종류          | 위치 (Portal)                      |
| ------------------ | ---------------------------------- |
| Function 실행 로그 | Functions → Monitor → Invocations  |
| Live stream 로그   | Functions → Monitor → Live Metrics |
| 앱 로그 (KQL 쿼리) | Monitor → Logs                     |

위 기능을 사용하려면 Application Insights가 필수이다.

---

## 비용 분석

### 요금 구조

| 항목        | 내용      | 비용     |
| ----------- | --------- | -------- |
| 데이터 수집 | 첫 5GB/월 | **무료** |
| 데이터 수집 | 초과분    | $2.30/GB |
| 데이터 보존 | 기본 90일 | **무료** |

> **주의**: 5GB 무료는 Application Insights 인스턴스 단위가 아니라, 연결된 **Log Analytics Workspace 전체 기준**으로 합산된다.  
> Classic Application Insights(구버전)는 인스턴스별 5GB 무료였으나, 현재 기본 방식인 Workspace-based는 Workspace 단위로 합산된다.

### 실제 데이터 규모 추정

- Function 실행 1회당 평균 로그 크기: **약 2 KB**
- 5GB = 약 **250만 건** 실행에 해당

| 고객사 규모               | 예상 월간 실행 횟수 | 예상 비용  |
| ------------------------- | ------------------- | ---------- |
| 소규모 스타트업           | 수만 건             | **$0**     |
| 중간 규모 (직원 50~200명) | 수십만 건           | **$0**     |
| 대기업                    | 수백만 건+          | $0~수 달러 |

Log Doctor 에이전트 자체가 추가하는 로그 데이터는 **수십 MB 이하** 수준으로, 고객사 기존 Azure 사용량에 미치는 영향은 미미하다.

---

## 고객사(SaaS 설치형) 고려사항

Log Doctor 에이전트는 **고객사 Azure 구독에 설치**되므로, 생성되는 Azure 리소스와 비용은 고객사가 부담한다.

- Log Doctor 에이전트가 추가하는 데이터량은 극히 적어 **기존 무료 범위 안에서 흡수**된다.
- 고객사가 이미 다른 Application Insights를 운영 중이라면, Log Analytics Workspace 전체 합산 기준으로 계산되므로 기존 사용량을 확인하는 것이 바람직하다.
- 계약/영업 시 아래와 같이 명시하면 충분하다:

  > _"Log Doctor 에이전트는 고객사 Azure 구독에 Application Insights 리소스를 추가 생성하지만, 5GB/월 무료 범위 내에서 동작합니다."_

---

## Bicep 구현

### 추가된 리소스 (`functions.bicep`)

```bicep
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${functionAppName}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    RetentionInDays: 30  // 비용 절감: 기본 90일 → 30일로 단축
  }
}
```

### Function App에 추가된 환경변수

```bicep
{ name: 'APPINSIGHTS_INSTRUMENTATIONKEY',           value: appInsights.properties.InstrumentationKey }
{ name: 'APPLICATIONINSIGHTS_CONNECTION_STRING',    value: appInsights.properties.ConnectionString }
{ name: 'ApplicationInsightsAgent_EXTENSION_VERSION', value: '~3' }
```

### 비용 절감 포인트

- `RetentionInDays: 30` — 기본 90일 대신 30일로 단축하여 장기 보존 비용 절감
