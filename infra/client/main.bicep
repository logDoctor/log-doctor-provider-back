targetScope = 'subscription'

var location = deployment().location

param appName string = 'logdoctor'

param resourceGroupName string = 'rg-logdoctor'

var env = 'prod'

@metadata({ hidden: true })
param providerUrl string = ''

@metadata({ hidden: true })
param packageUrl string = ''

@metadata({ hidden: true })
param providerClientId string = ''

@metadata({ hidden: true })
param providerPrincipalId string = ''

@metadata({ hidden: true })
@description('매 배포마다 고유 값을 전달하여 ARM이 설정 변경으로 인식하도록 합니다. Bicep 내부에서는 사용하지 않습니다.')
#disable-next-line no-unused-params
param deploymentId string = ''

var uniqueId = uniqueString(subscription().subscriptionId, subscription().tenantId)
var storageAccountName = 'st${toLower(uniqueId)}'
var functionAppName = '${appName}-${env}-fn-${uniqueId}'
var appServicePlanName = '${appName}-${env}-plan'

// 1. 리소스 그룹 생성 (구독 수준)
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

// 2. Azure Functions 배포 (생성된 리소스 그룹 내에 배포)
module functions 'modules/functions.bicep' = {
  scope: rg
  name: 'functions-deployment'
  params: {
    location: location
    functionAppName: functionAppName
    storageAccountName: storageAccountName
    appServicePlanName: appServicePlanName
    providerUrl: providerUrl
    tenantId: subscription().tenantId
    subscriptionId: subscription().subscriptionId
    packageUrl: packageUrl
    providerClientId: providerClientId
    providerPrincipalId: providerPrincipalId
  }
}

output functionAppUrl string = 'https://${functions.outputs.functionAppHostName}'
output resourceGroupId string = rg.id
