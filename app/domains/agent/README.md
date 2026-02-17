# Agent Domain

## 정의 (Definition)

고객사 환경에 배포된 로그 수집 에이전트(Log Collector)와의 통신 및 등록을 담당하는 도메인입니다.

## 역할 (Role)

- **에이전트 핸드셰이크**: 에이전트가 최초 배포되거나 재시작될 때 서버로 보내는 등록 신호를 처리합니다.
- **연동 상태 관리**: 에이전트의 버전 정보 및 연동 성공 여부를 DB에 기록하여 테넌트 상태에 반영합니다.

## 핵심 유즈케이스 (Core Use Cases)

- `AgentHandshaker`: 에이전트로부터 전달받은 정보를 검증하고, 성공적으로 연동되었음을 기록합니다.

## 의존성 관계 (Dependencies)

- **Repository**: `AgentRepository` (에이전트 연동 상태 저장)
- **Infra**: 없음
