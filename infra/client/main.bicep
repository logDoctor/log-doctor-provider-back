targetScope = 'subscription'

var location = deployment().location

@description('OpenAI 리소스가 배포될 리전입니다. gpt-4o가 안정적으로 지원되는 리전을 선택해주세요.')
@allowed([
  'eastus'
  'swedencentral'
  'westus3'
  'australiaeast'
])
param openAiLocation string = 'eastus'

param appName string = 'logdoctor'

param resourceGroupName string = 'rg-logdoctor'

var env = 'prod'

@metadata({ hidden: true })
param publisherUrl string = ''

@metadata({ hidden: true })
param packageUrl string = ''

@metadata({ hidden: true })
param publisherClientId string = ''

@metadata({ hidden: true })
param publisherPrincipalId string = ''

var uniqueId = uniqueString(subscription().subscriptionId, subscription().tenantId)
var storageAccountName = 'st${toLower(uniqueId)}'
var functionAppName = '${appName}-${env}-fn-${uniqueId}'
var appServicePlanName = '${appName}-${env}-plan'
// deployment().name은 Azure Portal에서 매 배포마다 자동 생성되는 고유 문자열입니다.
// 예: 'Microsoft.Template-20260318175426' → uniqueString으로 변환하여 8자리 고유 접미사를 만듭니다.
var openAiDeploymentSuffix = substring(uniqueString(deployment().name), 0, 8)
var openAiAccountName = '${appName}-${env}-openai-${uniqueId}-${openAiDeploymentSuffix}'

// 1. 리소스 그룹 생성 (구독 수준)
resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
}

// 2. OpenAI 배포
module openAi 'modules/openai.bicep' = {
  scope: rg
  name: 'openai-deployment'
  params: {
    location: openAiLocation
    openAiAccountName: openAiAccountName

  }
}

// 3. Azure Functions 배포 (생성된 리소스 그룹 내에 배포)
module functions 'modules/functions.bicep' = {
  scope: rg
  name: 'functions-deployment'
  params: {
    location: location
    functionAppName: functionAppName
    storageAccountName: storageAccountName
    appServicePlanName: appServicePlanName
    publisherUrl: publisherUrl
    tenantId: subscription().tenantId
    subscriptionId: subscription().subscriptionId
    packageUrl: packageUrl
    publisherClientId: publisherClientId
    publisherPrincipalId: publisherPrincipalId
    openAiEndpoint: openAi.outputs.endpoint
  }
}

output functionAppUrl string = 'https://${functions.outputs.functionAppHostName}'
output resourceGroupId string = rg.id

@description('생성할 커스텀 역할의 이름')
param scannerRoleName string = 'LogDoctor Diagnostic Scanner (Minimal)'

// 역할 이름이 변경되지 않는 한 동일한 GUID를 유지하도록 설정
var scannerRoleDefName = guid(subscription().id, scannerRoleName)

// 4. 커스텀 역할 정의 (구독 레벨)
resource customScannerRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' = {
  name: scannerRoleDefName
  properties: {
    roleName: scannerRoleName
    description: 'LogDoctor 진단을 위한 최소 읽기 권한 (인프라, 로그 쿼리, 진단 설정)'
    type: 'customRole'
    permissions: [
      {
        actions: [
          'Microsoft.ResourceGraph/resources/read'
          'Microsoft.Web/sites/Read'
          'Microsoft.Compute/virtualMachines/read'
          'Microsoft.Compute/virtualMachines/extensions/read'
          'Microsoft.OperationalInsights/workspaces/read'
          'Microsoft.OperationalInsights/workspaces/query/read'
          'Microsoft.Insights/Components/Read'
          'Microsoft.Insights/Logs/AppRequests/Read'
          'Microsoft.CognitiveServices/accounts/read'
          'Microsoft.CognitiveServices/accounts/deployments/read'
          'Microsoft.Insights/diagnosticSettings/read'
          'Microsoft.Insights/dataCollectionRuleAssociations/read'
        ]
        notActions: []
        dataActions: [
          'Microsoft.OperationalInsights/workspaces/tables/data/read'
        ]
        notDataActions: []
      }
    ]
    assignableScopes: [
      subscription().id
    ]
  }
}

// 5. LogDoctor Identity에 구독 레벨로 커스텀 역할 할당
module subscriptionRole 'modules/subscription-role.bicep' = {
  name: 'subscription-role-deployment'
  params: {
    principalId: functions.outputs.functionAppPrincipalId
    roleDefinitionId: customScannerRole.id
    roleAssignmentSeed: functionAppName
  }
}

// 5. OpenAI 런타임 추론 역할 할당 (리소스 그룹 레벨, 실제로는 해당 리소스 범위 내에서 적용)
module openaiRole 'modules/openai-inference-role.bicep' = {
  scope: rg
  name: 'openai-role-deployment'
  params: {
    logDoctorPrincipalId: functions.outputs.functionAppPrincipalId
    openAiAccountName: openAiAccountName
  }
}
