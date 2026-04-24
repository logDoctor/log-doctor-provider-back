from fastapi import Depends
from pydantic import BaseModel

from app.core.auth.guards import get_current_identity
from app.core.auth.models import Identity
from app.core.routing import APIRouter

router = APIRouter(tags=["Inspection Rules"])


class InspectionRuleItem(BaseModel):
    code: str
    title: str
    description: str
    icon: str


class EngineGroup(BaseModel):
    code: str
    name: str
    icon: str
    description: str
    rules: list[InspectionRuleItem]


class InspectionRulesResponse(BaseModel):
    engines: list[EngineGroup]


_INSPECTION_RULES_DATA = InspectionRulesResponse(
    engines=[
        EngineGroup(
            code="DET",
            name="탐지",
            icon="🔍",
            description="인프라 및 앱 성능/연결성 탐지",
            rules=[
                InspectionRuleItem(
                    code="DET-001",
                    title="수집기 상태 점검",
                    description="VM Extension 내 Azure Monitor Agent(AMA) 설치 및 동작 여부를 확인합니다.",
                    icon="🖥️",
                ),
                InspectionRuleItem(
                    code="DET-002",
                    title="리소스 활성 상태 검증",
                    description="LAW Heartbeat 테이블을 조회하여 리소스의 실제 생존 상태(Liveness)를 확인합니다.",
                    icon="💓",
                ),
                InspectionRuleItem(
                    code="DET-003",
                    title="연동 시스템 추적 투명도",
                    description="LAW AppDependencies 쿼리를 통해 OTel/SDK 분산 추적 유무를 판별합니다.",
                    icon="🕸️",
                ),
                InspectionRuleItem(
                    code="DET-004",
                    title="서비스 장애/지연 분석",
                    description="AppRequests KQL로 5xx 에러율 및 p95 응답 지연 성능 병목을 분석합니다.",
                    icon="⚠️",
                ),
            ],
        ),
        EngineGroup(
            code="PRV",
            name="예방",
            icon="🛡️",
            description="예방 및 가속 관리",
            rules=[
                InspectionRuleItem(
                    code="PRV-001",
                    title="운영 환경 디버그 로그 방지",
                    description="운영 환경에서 불필요하게 수집되는 디버그 레벨 로그를 감지하고 차단합니다.",
                    icon="🐛",
                ),
                InspectionRuleItem(
                    code="PRV-002",
                    title="고빈도 노이즈 로그 최적화",
                    description="반복 메시지의 비용 낭비 및 LAW 내부 구조화 비율을 정밀 검사합니다.",
                    icon="🔊",
                ),
                InspectionRuleItem(
                    code="PRV-003",
                    title="로그 페이로드 사이즈 최적화",
                    description="과도한 페이로드 크기로 인한 수집 비용 증가를 탐지하고 최적화를 권고합니다.",
                    icon="📦",
                ),
            ],
        ),
        EngineGroup(
            code="FLT",
            name="필터",
            icon="🚰",
            description="필터링 및 여과",
            rules=[
                InspectionRuleItem(
                    code="FLT-001",
                    title="개인정보 감지/방지 (PII)",
                    description="AppTraces 대상 정규식 및 LLM 기반 패턴 매칭으로 개인정보 평문 노출을 검사합니다.",
                    icon="🔒",
                ),
                InspectionRuleItem(
                    code="FLT-002",
                    title="상태/에러 컨텍스트 진단",
                    description="진단 설정은 있으나 상태·에러 컨텍스트 정보가 누락된 리소스를 검사합니다.",
                    icon="⚙️",
                ),
                InspectionRuleItem(
                    code="FLT-003",
                    title="고빈도 단순 API 샘플화 추천",
                    description="단순 반복 API 호출에 대해 샘플링 적용을 권고하여 수집 비용을 절감합니다.",
                    icon="📊",
                ),
            ],
        ),
        EngineGroup(
            code="RET",
            name="보존",
            icon="🌿",
            description="보존 및 관리",
            rules=[
                InspectionRuleItem(
                    code="RET-001",
                    title="로그 요금 누수 및 과금 경보",
                    description="단순 반복 텍스트 로그가 발생시키는 추정 요금 낭비액을 분석하고 경보합니다.",
                    icon="💸",
                ),
                InspectionRuleItem(
                    code="RET-002",
                    title="보존일수/요금제 최적화 권고",
                    description="현재 보존 기간 및 요금제 설정을 분석하여 비용 최적화 방안을 권고합니다.",
                    icon="🌿",
                ),
            ],
        ),
    ]
)


@router.get("/", response_model=InspectionRulesResponse)
async def get_inspection_rules(
    identity: Identity = Depends(get_current_identity),
) -> InspectionRulesResponse:
    """4대 엔진 기반 진단 규칙 목록을 반환합니다."""
    return _INSPECTION_RULES_DATA
