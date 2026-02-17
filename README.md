# Log Doctor Provider Backend

Azure 기반 인프라 로깅 및 진단을 위한 로그 닥터 서비스의 백엔드 시스템입니다.

## 🚀 개요

본 프로젝트는 **Resource-Driven Architecture**와 **Clean Architecture** 원칙에 따라 설계되었습니다. 각각의 비즈니스 리소스를 독립된 도메인으로 분리하고, 기술적인 세부 사항(DB, 외부 API)과 비즈니스 로직을 엄격히 격리함으로써 확장성과 유지보수성을 극대화했습니다.

## 🛡️ 주요 기술 스택

- **Framework**: FastAPI (Python 3.12+)
- **Package Manager**: [uv](https://github.com/astral-sh/uv) (빠르고 현대적인 패키지 관리 도구)
- **Database**: Azure Cosmos DB Serverless
- **Authentication**: Managed Identity (DefaultAzureCredential), Azure AD OBO Flow
- **API Client**: HTTPX (Asynchronous HTTP Client)

## 🏗️ 아키텍처 구조

### 1. 계층형 구조 (Clean Architecture)

전체 시스템은 다음과 같은 논리적 계층으로 구성됩니다:

- **Core Layer (`app/core`)**: 전역 설정(Config) 및 전역 보안 로직(OBO Token Exchange 등). 어느 리소스에도 종속되지 않는 전역 정책을 담당합니다.
- **API Layer (`app/api`)**: API 버저닝 관리 계층입니다. `v1/router.py`에서 도메인 라우터를 통합합니다. 엔드포인트는 **Class-Based View (CBV)** 패턴을 사용하여 관리합니다.
- **Infra Layer (`app/infra`)**: 외부 세계와의 연결을 담당합니다.
  - `infra/external`: 외부 API(Azure ARM 등)와의 데이터 통신 세션 관리.
  - `infra/db`: 데이터베이스(Cosmos DB) 연결 및 클라이언트 팩토리.
- **Domain Layer (`app/domains`)**: 실제 비즈니스 가치를 창출하는 핵심 계층입니다. 리소스별로 폴더가 분리되어 있습니다.
- **Common Layer (`app/common`)**: 프로젝트 전반에서 재사용되는 유틸리티.

### 2. 도메인 내부 구조 (Resource-Driven)

각 도메인(예: `tenant`, `subscription`)은 아래와 같은 일관된 구조를 가집니다:

```text
app/domains/{resource}/
├── router.py        # 엔드포인트 정의
├── schemas.py       # 데이터 모델 (Pydantic)
├── dependencies.py  # 의존성 주입 (Provider)
├── repository.py    # 데이터 접근 추상화 (ABC Interface + Concrete Implementation)
└── services/        # 비즈니스 로직 (Use Case Pattern)
    ├── use_case_1.py
    └── use_case_2.py
```

## 🛠️ 주요 디자인 패턴

### 1. Use Case Pattern

하나의 서비스 클래스에 모든 로직을 몰아넣지 않고, 각 비즈니스 기능별로 작은 클래스/함수로 분리합니다. 이를 통해 **단일 책임 원칙(SRP)**을 준수하고 코드 가독성을 높입니다.

### 2. Repository Pattern (DIP)

비즈니스 로직은 실제 DB 엔진(Cosmos, SQL 등)을 몰라야 합니다.

- `ABC`(Abstract Base Class)를 사용하여 인터페이스를 정의합니다.
- 인터페이스와 구현체를 분리하여, 서비스 계층은 오직 인터페이스에만 의존하게 합니다 (**의존성 역전 원칙**).

### 3. Managed Identity

보안 강화를 위해 연결 문자열(Connection String)이나 키(Key)를 코드나 설정 파일에 저장하지 않습니다. Azure의 **Managed Identity**를 사용하여 인증 처리를 자동화하였습니다.

### 3. Service Naming Convention (Use Case)

각 서비스는 하나의 명확한 비즈니스 유즈케이스를 담당하며, 다음과 같은 명칭 규칙을 따릅니다:

- **파일명**: `snake_case`로 작성하며, 행동의 주체를 명시합니다. (예: `tenant_status_checker.py`)
- **클래스명**: `PascalCase`로 작성하며, 명사+동사(er/or) 형태를 권장합니다. (예: `TenantStatusChecker`, `SubscriptionFetcher`)
- **역할**: 서비스는 오직 하나의 책임(Action)을 가지거나, 관련된 작은 행동들의 집합으로 구성됩니다.

## 📂 디렉토리 상세 내역

- `app/main.py`: 애플리케이션 진입점 및 라우터 등록.
- `app/core/config.py`: Pydantic Settings 기반 환경 변수 관리.
- `app/core/security.py`: MSAL 기반 Azure AD 인증 로직.
- `app/infra/api/azure_client.py`: Azure REST API 호출을 위한 순수 클라이언트 팩토리.
- `app/infra/db/cosmos.py`: Cosmos DB 싱글톤 클라이언트 관리.
- `app/domains/tenant`: 테넌트 등록 및 상태 관리.
- `app/domains/subscription`: Azure 구독 정보 조회.
- `app/domains/agent`: 진단 에이전트 핸드쉐이크 및 관리.

## ⚙️ 설정 및 실행 (Setup & Run)

1. **의존성 설치**: `uv sync`
2. **환경 변수 설정**: `.env.example`을 복사하여 `.env`를 생성하고 값을 입력합니다.
   - 로컬 개발 시: `AUTH_METHOD=secret` (시크릿 사용) 또는 `managed_identity` (`az login` 사용)
3. **실행**: `uv run uvicorn app.main:app --reload`

```bash
# uv를 사용하여 의존성 설치 및 실행
uv run uvicorn app.main:app --port 8000 --reload
```

## 🐳 Docker 실행

```bash
# 이미지 빌드
docker build -t log-doctor-provider-back .

# 컨테이너 실행
docker run -p 8000:8000 log-doctor-provider-back
```

## 🧪 테스트 실행

```bash
# 전체 테스트 수행
uv run pytest
```

## 📝 개발 규칙

- **Git**: 커밋은 기능 단위로 최대한 작게 쪼개서 작성합니다.
- **Linting/Formatting**: Python 표준 스타일(PEP 8)을 준수합니다.
- ****init**.py (Shortcut Imports)**: `app/core`나 `app/infra`와 같이 자주 참조되는 핵심 패키지는 `__init__.py`를 통해 주요 객체를 노출합니다. 이를 통해 클라이언트 코드가 파일 내부 구조를 몰라도 `from app.core import settings`와 같이 간결하게 임포트할 수 있게 합니다.
