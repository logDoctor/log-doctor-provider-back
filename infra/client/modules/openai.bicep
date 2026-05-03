param location string
param openAiAccountName string
param modelDeploymentName string = 'gpt-4o'
param openAiModelCapacity int = 10 // 핵심: 기본 할당량 내 배포를 위한 안전한 수치 (10K TPM)


resource openAiAccount 'Microsoft.CognitiveServices/accounts@2023-05-01' = {
  name: openAiAccountName
  location: location
  kind: 'OpenAI'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: openAiAccountName
    publicNetworkAccess: 'Enabled'
  }
}

resource openAiDeployment 'Microsoft.CognitiveServices/accounts/deployments@2023-05-01' = {
  parent: openAiAccount
  name: modelDeploymentName
  sku: {
    name: 'Standard'
    capacity: openAiModelCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4o'
      version: '2024-11-20'
    }
  }
}

output endpoint string = openAiAccount.properties.endpoint
output openAiAccountId string = openAiAccount.id
