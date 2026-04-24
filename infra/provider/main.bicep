param location string = resourceGroup().location
param appName string = 'logdoctor'

@allowed(['dev', 'prod'])
param env string
param acrSku string 
param image string = ''
param entraClientId string = ''
param authMethod string = 'managed_identity'
@secure()
param entraClientSecret string = ''
param entraTenantId string = ''
param bootstrapOnly bool = false
param tabResourceDomain string = ''
param teamsAppId string = ''
param tenantAdminRoleId string = ''
param privilegedUserRoleId string = ''
param platformAdminRoleId string = ''

var baseName = '${appName}-${env}'

// 1. Log Analytics 배포
module law 'modules/law.bicep' = {
  name: 'law-deployment'
  params: {
    location: location
    lawName: '${baseName}-law'
  }
}

// 2. ACR 배포
module acr 'modules/acr.bicep' = {
  name: 'acr-deployment'
  params: {
    location: location
    acrName: 'acr${appName}${env}${uniqueString(resourceGroup().id)}'
    skuName: acrSku
    logAnalyticsWorkspaceId: law.outputs.lawId
  }
}

// 3. Cosmos DB 배포
module cosmos 'modules/cosmos.bicep' = if (!bootstrapOnly) {
  name: 'cosmos-deployment'
  params: {
    location: location
    cosmosAccountName: '${baseName}-cosmos-${uniqueString(resourceGroup().id)}'
    databaseName: 'log-doctor-db'
    logAnalyticsWorkspaceId: law.outputs.lawId
  }
}

// 4. Entra ID App Registration 배포 (수동 등록 앱 사용을 위해 주석 처리)
/*
module entraApp 'modules/entra-id.bicep' = if (!bootstrapOnly) {
  name: 'entra-id-deployment'
  params: {
    appDisplayName: 'Log Doctor (${env})'
    // ACA 배포 전에는 정확한 URL을 알기 어려우므로 우선 placeholder를 넣거나 
    // 로컬 개발용 URL 등을 기본값으로 활용할 수 있습니다.
    replyUrl: 'https://localhost:3000' 
  }
}
*/

// 5. Storage 리소스 배포
module storage 'modules/storage.bicep' = if (!bootstrapOnly) {
  name: 'storage-deployment'
  params: {
    location: location
    storageAccountName: take('st${appName}${env}${uniqueString(resourceGroup().id)}', 24)
    logAnalyticsWorkspaceId: law.outputs.lawId
  }
}

// 6. ACA 배포 (앞서 배포된 리소스들의 Output을 파라미터로 주입)
module aca 'modules/aca.bicep' = if (!bootstrapOnly) {
  name: 'aca-deployment'
  params: {
    location: location
    acaName: '${baseName}-aca'
    environmentName: '${baseName}-env'
    lawCustomerId: law.outputs.customerId
    lawSharedKey: law.outputs.sharedKey
    acrId: acr.outputs.acrId
    cosmosAccountId: (!bootstrapOnly) ? cosmos.outputs.cosmosAccountId : ''
    cosmosEndpoint: (!bootstrapOnly) ? cosmos.outputs.cosmosEndpoint : ''
    cosmosKey: (!bootstrapOnly) ? cosmos.outputs.cosmosKey : ''
    databaseName: 'log-doctor-db'
    storageAccountId: (!bootstrapOnly) ? storage.outputs.storageAccountId : ''
    storageAccountName: (!bootstrapOnly) ? storage.outputs.storageAccountName : ''
    storageConnectionString: (!bootstrapOnly) ? storage.outputs.storageConnectionString : ''
    entraClientId: entraClientId
    logAnalyticsWorkspaceId: law.outputs.lawId
    image: image
    acrPassword: acr.outputs.acrPassword
    authMethod: authMethod
    entraClientSecret: entraClientSecret
    entraTenantId: entraTenantId
    tabResourceDomain: tabResourceDomain
    teamsAppId: teamsAppId
    tenantAdminRoleId: tenantAdminRoleId
    privilegedUserRoleId: privilegedUserRoleId
    platformAdminRoleId: platformAdminRoleId
  }
}

output applicationUrl string = (!bootstrapOnly && (aca.?outputs != null)) ? aca.outputs.acaUrl : ''
output entraClientId string = entraClientId

