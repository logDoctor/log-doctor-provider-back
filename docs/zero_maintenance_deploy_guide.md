# Zero-Maintenance Deployment Guide (GitHub Actions + Azure OIDC)

`deploy.yml`에서 `secrets.PROVIDER_UPLOAD_TOKEN`을 매번 수동으로 업데이트하는 문제를 해결하기 위해 **Azure OIDC (OpenID Connect)**를 사용한 자동화 방식을 권장합니다.

## 1. 전제 조건 (Azure 설정)

1.  **Entra ID App Registration** 생성 (예: `logdoctor-cicd`)
2.  **Federated Credentials** 설정:
    - GitHub Actions를 신뢰하도록 설정 (Repository: `<user>/<repo>`, Branch: `main` 등)
3.  **App 역할 부여**: 공급자 백엔드 API에 접근할 수 있는 권한 부여.

## 2. GitHub Secrets 등록

GitHub에는 다음 3가지만 등록하면 됩니다. (이 값들은 바뀌지 않습니다.)

- `AZURE_CLIENT_ID`: App Registration의 Application ID
- `AZURE_TENANT_ID`: Entra ID의 Tenant ID
- `AZURE_SUBSCRIPTION_ID`: Azure Subscription ID
- `PROVIDER_URL`: 공급자 백엔드 URL

## 3. 업데이트된 `deploy.yml` (OIDC 방식)

```yaml
jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write # OIDC를 위해 필수!
      contents: read
    steps:
      - uses: actions/checkout@v4

      # 1. Azure Login (OIDC 사용)
      - name: Az Login
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}

      # 2. Access Token 실시간 발급
      - name: Get Access Token
        id: get_token
        run: |
          # 백엔드 API 서버를 Audience로 지정하여 토큰 획득
          TOKEN=$(az account get-access-token --resource ${{ secrets.AZURE_CLIENT_ID }} --query accessToken -o tsv)
          echo "::add-mask::$TOKEN"
          echo "token=$TOKEN" >> $GITHUB_OUTPUT

      # 3. 실시간 토큰을 사용하여 업로드
      - name: Upload to Provider Backend
        env:
          PROVIDER_URL: ${{ secrets.PROVIDER_URL }}
          UPLOAD_TOKEN: ${{ steps.get_token.outputs.token }}
        run: |
          curl -f -X POST "${PROVIDER_URL}/api/v1/packages/upload" \
            -H "Authorization: Bearer $UPLOAD_TOKEN" \
            -F "file=@agent.zip"
```

## 4. 이 방식의 장점

- **무기한 사용 가능**: 시크릿 만료로 인해 배포가 깨질 일이 없습니다.
- **보안성**: 1시간만 유효한 임시 토큰이 매번 생성되므로 매우 안전합니다.
- **관리 최소화**: GitHub에 로그인 비밀번호(Secret)를 저장하지 않습니다.
