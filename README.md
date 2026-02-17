# log-doctor-backend

온보딩(Onboarding) 도메인

1. 상태 확인 (1단계): 프론트가 준 SSO 토큰을 까보고, 우리 DB에 가입된 테넌트인지 확인.
2. OBO 및 구독 조회 (2단계): SSO 토큰을 ARM 토큰으로 교환(OBO)하고, Azure API를 찔러서 구독 리스트 반환.
3. 배포 완료 핸드셰이크 (4단계): 고객사 에이전트(Function App)가 켜지면서 보내는 Webhook 수신 및 DB 업데이트.
