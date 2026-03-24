targetScope = 'resourceGroup'

@description('LogDoctor 앱의 Managed Identity 또는 Service Principal의 Object ID')
param logDoctorPrincipalId string

@description('사용할 Azure OpenAI 리소스의 이름')
param openAiAccountName string

// 빌트인 역할: Cognitive Services OpenAI User 의 Role ID
var openAiUserRoleId = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

// 기존에 배포된 Azure OpenAI 리소스 참조
resource openAiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' existing = {
  name: openAiAccountName
}

// 3. 대상 OpenAI 리소스에만 엄격하게 권한 할당 (Scope 지정)
resource openAiRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  // 리소스 ID, 역할 ID, Principal ID를 조합하여 고유하고 멱등성 있는 GUID 생성
  name: guid(openAiAccount.id, openAiUserRoleId, logDoctorPrincipalId)
  scope: openAiAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRoleId)
    principalId: logDoctorPrincipalId
    principalType: 'ServicePrincipal'
  }
}
