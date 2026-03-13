param location string
param functionAppName string
param storageAccountName string
param appServicePlanName string
param providerUrl string
param tenantId string
param subscriptionId string
param packageUrl string = ''
param providerClientId string = ''
param providerPrincipalId string = ''

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    supportsHttpsTrafficOnly: true
    defaultToOAuthAuthentication: true
  }
}

resource queueService 'Microsoft.Storage/storageAccounts/queueServices@2023-01-01' = {
  parent: storageAccount
  name: 'default'
}

resource analysisRequestsQueue 'Microsoft.Storage/storageAccounts/queueServices/queues@2023-01-01' = {
  parent: queueService
  name: 'analysis-requests'
}



resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${functionAppName}-law'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018' // 종량제 (5GB 무료 적용됨)
    }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${functionAppName}-insights'
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id // 명시적 연결
    RetentionInDays: 30
  }
}

resource hostingPlan 'Microsoft.Web/serverfarms@2023-01-01' = {
  name: appServicePlanName
  location: location
  kind: 'linux'
  sku: {
    name: 'Y1'
    tier: 'Dynamic'
  }
  properties: {
    reserved: true
  }
}

resource functionApp 'Microsoft.Web/sites@2023-01-01' = {
  name: functionAppName
  location: location
  kind: 'functionapp,linux'
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    serverFarmId: hostingPlan.id
    siteConfig: {
      linuxFxVersion: 'Python|3.11'
      appSettings: [
        {
          name: 'AzureWebJobsStorage'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTAZUREFILECONNECTIONSTRING'
          value: 'DefaultEndpointsProtocol=https;AccountName=${storageAccountName};EndpointSuffix=${environment().suffixes.storage};AccountKey=${storageAccount.listKeys().keys[0].value}'
        }
        {
          name: 'WEBSITE_CONTENTSHARE'
          value: toLower(functionAppName)
        }
        {
          name: 'FUNCTIONS_EXTENSION_VERSION'
          value: '~4'
        }
        {
          name: 'FUNCTIONS_WORKER_RUNTIME'
          value: 'python'
        }
        {
          name: 'PROVIDER_URL'
          value: providerUrl
        }
        {
          name: 'TENANT_ID'
          value: tenantId
        }
        {
          name: 'SUBSCRIPTION_ID'
          value: subscriptionId
        }
        {
          name: 'PROVIDER_CLIENT_ID'
          value: providerClientId
        }
        {
          name: 'RESOURCE_GROUP_NAME'
          value: resourceGroup().name
        }
        {
          name: 'FUNCTION_APP_NAME'
          value: functionAppName
        }
        {
          name: 'LOCATION'
          value: location
        }
        {
          name: 'ENVIRONMENT'
          value: 'prod'  // TODO: Add environment parameter if needed, defaulting to prod for now
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: packageUrl
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'ApplicationInsightsAgent_EXTENSION_VERSION'
          value: '~3'
        }
      ]
    }
    httpsOnly: true
  }
}

// --- RBAC Role Assignments ---

// Storage Queue Data Message Sender 역할 정의 (Built-in)
resource storageQueueDataMessageSenderRole 'Microsoft.Authorization/roleDefinitions@2022-04-01' existing = {
  scope: subscription()
  name: 'c6a89b2d-59bc-44d0-9896-0f6e12d7b80a'
}
resource providerQueueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(providerPrincipalId)) {
  name: guid(storageAccount.id, providerPrincipalId, storageQueueDataMessageSenderRole.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: storageQueueDataMessageSenderRole.id
    principalId: providerPrincipalId
    principalType: 'ServicePrincipal'
  }
}

output functionAppHostName string = functionApp.properties.defaultHostName
