#!/bin/bash

# Provider Backend "One-Stop" 배포 자동화 스크립트
# 리소스 그룹 생성, ACR 초기화, 이미지 빌드, ACA 배포를 한 번에 처리합니다.
# Usage: ./scripts/deploy-provider.sh <env> <resource-group-name> [entra-client-id] [location]
# Example: ./scripts/deploy-provider.sh dev logdoctor-dev-rg 2bc30b69-1a29-4079-8a7b-eddd486508bb koreacentral

set -e

# .env 파일 로드 (존재하는 경우)
if [ -f .env ]; then
    echo ">>> .env 파일에서 설정 로드 중..."
    # 주석 제외하고 export
    export $(grep -v '^#' .env | xargs)
fi

ENV=${1:-"dev"}
RG_NAME=${2:-"logdoctor"}
# 파라미터가 없으면 .env의 CLIENT_ID 사용
ENTRA_ID=${3:-$CLIENT_ID}
LOCATION=${4:-"koreacentral"}

# .env에서 읽어온 값들을 Bicep 파라미터 형식으로 정리
AUTH_METHOD=${AUTH_METHOD:-"managed_identity"}
ENTRA_TENANT_ID=${TENANT_ID:-""}
ENTRA_CLIENT_SECRET=${CLIENT_SECRET:-""}

if [ -z "$ENV" ] || [ -z "$RG_NAME" ]; then
    echo "Usage: $0 <env> <resource-group-name> [entra-client-id] [location]"
    exit 1
fi

echo ">>> [0/5] Client ARM 템플릿 빌드 (infra/client/main.bicep → client-setup.json)"
az bicep build \
  --file infra/client/main.bicep \
  --outfile infra/client/client-setup.json
echo "    - client-setup.json 업데이트 완료."

echo ">>> [1/5] 리소스 그룹 확인 중: $RG_NAME ($LOCATION)"
if [ "$(az group exists --name "$RG_NAME")" = "false" ]; then
    echo "    - 리소스 그룹이 없습니다. 생성을 시작합니다..."
    az group create --name "$RG_NAME" --location "$LOCATION"
    echo "    - 리소스 그룹 생성 완료."
else
    echo "    - 리소스 그룹이 이미 존재합니다."
fi

echo ">>> [2/5] 인프라 상태 확인 (ACR 존재 여부)"
ACR_NAME=$(az acr list --resource-group "$RG_NAME" --query "[0].name" -o tsv)

if [ -z "$ACR_NAME" ]; then
    echo "    - ACR을 찾을 수 없습니다. 기초 인프라(Bootstrap) 배포를 시작합니다..."
    PARAM_ENTRA_CLI=""
    if [ -n "$ENTRA_ID" ]; then
        PARAM_ENTRA_CLI="--parameters entraClientId=${ENTRA_ID}"
    fi

    # bootstrapOnly=true로 설정하여 LAW와 ACR만 먼저 배포
    az deployment group create \
      --name "bootstrap-${IMAGE_TAG}" \
      --resource-group "$RG_NAME" \
      --template-file infra/provider/main.bicep \
      --parameters "infra/provider/main.${ENV}.bicepparam" \
      --parameters bootstrapOnly=true \
      $PARAM_ENTRA_CLI

    ACR_NAME=$(az acr list --resource-group "$RG_NAME" --query "[0].name" -o tsv)
    echo "    - 기초 인프라(ACR/LAW) 배포 완료."
else
    echo "    - ACR($ACR_NAME)이 이미 존재합니다."
fi

IMAGE_TAG=$(date +%Y%m%d%H%M%S)
IMAGE_NAME="${ACR_NAME}.azurecr.io/log-doctor-back:${IMAGE_TAG}"

echo ">>> [3/5] 실제 백엔드 소스 빌드"
if az acr build --registry "$ACR_NAME" --image "log-doctor-back:${IMAGE_TAG}" . ; then
    echo "    - ACR Cloud Build 성공."
else
    echo "    - ACR Cloud Build가 구독 정책 등으로 인해 제한되었습니다 (TasksOperationsNotAllowed)."
    echo "    - 로컬 Docker를 사용하여 빌드 및 푸시를 시도합니다..."
    
    if ! command -v docker &> /dev/null; then
        echo "Error: 로컬에 Docker가 설치되어 있지 않거나 실행 중이 아닙니다. Docker를 실행해 주세요."
        exit 1
    fi

    # ACR 로그인
    az acr login --name "$ACR_NAME"
    
    # 로컬 빌드 및 푸시 (Azure는 linux/amd64 아키텍처를 요구함)
    docker build --platform linux/amd64 -t "$IMAGE_NAME" .
    docker push "$IMAGE_NAME"
    echo "    - 로컬 Docker 빌드 및 푸시 완료."
fi

echo ">>> [4/5] 전체 서비스 인프라 배포 (ACA/Cosmos 등)"
PARAM_EXTRA="--parameters authMethod=${AUTH_METHOD} entraClientId=${ENTRA_ID} entraTenantId=${ENTRA_TENANT_ID} entraClientSecret=${ENTRA_CLIENT_SECRET}"

DEPLOY_NAME="service-deploy-${IMAGE_TAG}"
# bootstrapOnly=false(기본값)로 설정하여 전체 리소스 배포 및 이미지 교체
az deployment group create \
  --name "$DEPLOY_NAME" \
  --resource-group "$RG_NAME" \
  --template-file infra/provider/main.bicep \
  --parameters "infra/provider/main.${ENV}.bicepparam" \
  --parameters image="${IMAGE_NAME}" \
  --parameters bootstrapOnly=false \
  $PARAM_EXTRA

echo ">>> [5/5] 배포 완료!"
APPLICATION_URL=$(az deployment group show -g "$RG_NAME" -n "$DEPLOY_NAME" --query "properties.outputs.applicationUrl.value" -o tsv)
echo "--------------------------------------------------"
echo " 접속 URL: https://${APPLICATION_URL}"
echo "--------------------------------------------------"
