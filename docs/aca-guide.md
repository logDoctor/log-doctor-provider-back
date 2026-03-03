# Azure Container Apps (ACA) 배포 가이드

## 1. 사전 준비 (Prerequisites)

- Azure CLI 설치 (`brew install azure-cli`)
- `az login` 완료

## 2. 배포 스크립트 작성 (`deploy.sh`)

```bash
#!/bin/bash

# 변수 설정
RESOURCE_GROUP="rg-log-doctor"
LOCATION="koreacentral"
ACR_NAME="acrlogdoctor"
ACA_ENV="aca-env-log-doctor"
APP_NAME="log-doctor-provider-back"
IMAGE_TAG="latest"

# 1. 리소스 그룹 생성
az group create --name $RESOURCE_GROUP --location $LOCATION

# 2. ACR 생성 및 로그인
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true
az acr login --name $ACR_NAME

# 3. 이미지 빌드 및 푸시 (M1 Mac 이슈 방지를 위해 buildx 사용 권장)
# docker buildx build --platform linux/amd64 -t $ACR_NAME.azurecr.io/$APP_NAME:$IMAGE_TAG --push .
az acr build --registry $ACR_NAME --image $APP_NAME:$IMAGE_TAG .

# 4. ACA 환경 생성
az containerapp env create --name $ACA_ENV --resource-group $RESOURCE_GROUP --location $LOCATION

# 5. 앱 배포 (Managed Identity 활성화)
az containerapp create \
  --name $APP_NAME \
  --resource-group $RESOURCE_GROUP \
  --environment $ACA_ENV \
  --image $ACR_NAME.azurecr.io/$APP_NAME:$IMAGE_TAG \
  --target-port 8000 \
  --ingress external \
  --mi-system-assigned \
  --env-vars AUTH_METHOD=managed_identity \
             COSMOS_ENDPOINT=https://your-cosmos-db.documents.azure.com:443/ \
             COSMOS_DATABASE=log-doctor-db \
             AZURE_COSMOS_DISABLE_SSL=false
```

## 3. 주요 포인트

1. **Ingress**: `--target-port 8000`을 명시해야 FastAPI 포트와 연결됩니다.
2. **ACR Integration**: ACA가 ACR에서 이미지를 가져올 수 있도록 권한을 부여합니다.
3. **Managed Identity**: `--mi-system-assigned` 플래그로 시스템 할당 ID를 켭니다. 이후 Azure Portal에서 이 Identity에 Cosmos DB 접근 권한(`Cosmos DB Data Contributor` 등)을 부여해야 합니다.
4. **Environment Variables**: `CLIENT_ID` (Managed Identity의 ID) 등을 ACA 설정에 주입합니다.
