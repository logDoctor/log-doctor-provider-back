from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class Agent:
    id: str  # tenant_id:agent_id format for CosmosDB
    tenant_id: str
    subscription_id: str
    resource_group_name: str
    function_app_name: str
    location: str
    environment: str
    runtime_env: dict
    client_ip: str
    agent_id: str
    version: str
    capabilities: list[str]  # 에이전트의 주요 기능 (detect, filter, retain 등)
    status: str
    analysis_schedule: str
    last_handshake_at: str
    deleted_at: str | None = None

    @staticmethod
    def create(
        tenant_id: str,
        subscription_id: str,
        resource_group_name: str,
        function_app_name: str,
        location: str,
        environment: str,
        runtime_env: dict,
        client_ip: str,
        agent_id: str,
        version: str,
        capabilities: list[str]
    ) -> "Agent":
        """최초 에이전트 도메인 객체를 생성하는 팩토리 메서드입니다."""
        now = datetime.now(UTC).isoformat()
        return Agent(
            id=f"{tenant_id}:{agent_id}",
            tenant_id=tenant_id,
            subscription_id=subscription_id,
            resource_group_name=resource_group_name,
            function_app_name=function_app_name,
            location=location,
            environment=environment,
            runtime_env=runtime_env,
            client_ip=client_ip,
            agent_id=agent_id,
            version=version,
            capabilities=capabilities,
            status="INITIALIZING",
            analysis_schedule="0 0 * * *",  # Default: 매일 자정
            last_handshake_at=now,
            deleted_at=None,
        )

    @staticmethod
    def from_dict(data: dict) -> "Agent":
        """Cosmos DB 데이터로부터 에이전트 도메인 객체를 복원합니다."""
        return Agent(
            id=data["id"],
            tenant_id=data["tenant_id"],
            subscription_id=data["subscription_id"],
            resource_group_name=data["resource_group_name"],
            function_app_name=data.get("function_app_name", ""),
            location=data.get("location", ""),
            environment=data.get("environment", ""),
            runtime_env=data.get("runtime_env", {}),
            client_ip=data.get("client_ip", ""),
            agent_id=data["agent_id"],
            version=data["version"],
            capabilities=data.get("capabilities", []),
            status=data.get("status", "UNKNOWN"),
            analysis_schedule=data.get("analysis_schedule", "0 0 * * *"),
            last_handshake_at=data["last_handshake_at"],
            deleted_at=data.get("deleted_at"),
        )

    def to_dict(self) -> dict:
        """Cosmos DB 저장을 위한 사전 형태로 변환합니다."""
        result = {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "subscription_id": self.subscription_id,
            "resource_group_name": self.resource_group_name,
            "function_app_name": self.function_app_name,
            "location": self.location,
            "environment": self.environment,
            "runtime_env": self.runtime_env,
            "client_ip": self.client_ip,
            "agent_id": self.agent_id,
            "version": self.version,
            "capabilities": self.capabilities,
            "status": self.status,
            "analysis_schedule": self.analysis_schedule,
            "last_handshake_at": self.last_handshake_at,
        }
        if self.deleted_at:
            result["deleted_at"] = self.deleted_at
        return result

    def is_same_version(self, version: str) -> bool:
        """버전 정보가 일치하는지 확인합니다."""
        return self.version == version

    def update_version(self, version: str):
        """에이전트 버전을 업데이트하고 핸드쉐이크 시간을 갱신합니다."""
        self.version = version
        self.last_handshake_at = datetime.now(UTC).isoformat()

    def update(
        self,
        version: str | None = None,
        status: str | None = None,
        analysis_schedule: str | None = None,
    ) -> list[str]:
        """필드 정보를 업데이트하고 변경된 필드 목록을 반환합니다."""
        updated_fields = []
        if version and self.version != version:
            self.version = version
            updated_fields.append("version")
        if status and self.status != status:
            self.status = status
            updated_fields.append("status")
        if analysis_schedule and self.analysis_schedule != analysis_schedule:
            self.analysis_schedule = analysis_schedule
            updated_fields.append("analysis_schedule")

        if updated_fields:
            self.last_handshake_at = datetime.now(UTC).isoformat()

        return updated_fields

    def deactivate(self):
        """에이전트를 비활성화 상태로 전환합니다. (Azure 리소스 삭제 진행 중)"""
        self.status = "DEACTIVATING"

    def confirm_deletion(self):
        """Azure 리소스 삭제가 확인된 후 최종 삭제 상태로 전환합니다."""
        self.status = "DELETED"
        self.deleted_at = datetime.now(UTC).isoformat()

    def mark_deactivate_failed(self):
        """Azure 리소스 삭제가 실패하여 비활성화에 실패했음을 표시합니다."""
        self.status = "DEACTIVATE_FAILED"
