# License Domain

## 정의 (Definition)

Log Doctor 서비스의 이용 권한 및 요금제(License)를 관리하는 도메인입니다.

## 역할 (Role)

- **라이선스 확인**: 테넌트의 구독 등급에 따른 기능 제한 및 유효 기간을 검증합니다.

## 핵심 유즈케이스 (Core Use Cases)

- `LicenseValidator` (TBD): 현재 테넌트의 라이선스 상태를 확인하고 권한을 부여합니다.

## 의존성 관계 (Dependencies)

- **Repository**: 라이선스 관리용 별도 스토리지 예정
