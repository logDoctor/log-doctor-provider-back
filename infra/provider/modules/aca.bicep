param location string
param acaName string
param environmentName string
param targetPort int = 8000
param image string

// 다른 모듈에서 넘겨받을 연동 값들
param lawCustomerId string
@secure()
param lawSharedKey string
param acrId string
@secure()
param acrPassword string
param cosmosAccountId string
param cosmosEndpoint string
param databaseName string
param logAnalyticsWorkspaceId string
param storageAccountId string = ''
param storageAccountName string = ''
param cosmosKey string = ''
param storageConnectionString string = ''

// 추가 옵션
param authMethod string = 'managed_identity'
param entraClientId string
@secure()
param entraClientSecret string = ''
param entraTenantId string = ''
param tabResourceDomain string = ''
param tenantAdminRoleId string = ''
param privilegedUserRoleId string = ''
param platformAdminRoleId string = ''
param teamsAppId string = ''

// 1. ACA 환경 (Managed Environment)
resource cae 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: lawCustomerId
        sharedKey: lawSharedKey
      }
    }
  }
}

resource diagnosticSettings 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: '${cae.name}-diag'
  scope: cae
  properties: {
    workspaceId: logAnalyticsWorkspaceId
    metrics: [{ category: 'AllMetrics', enabled: true }]
  }
}


// 2. Container App (SystemAssigned Identity 활성화)
resource aca 'Microsoft.App/containerApps@2023-05-01' = {
  name: acaName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    managedEnvironmentId: cae.id
    configuration: {
      ingress: {
        external: true
        targetPort: targetPort
        corsPolicy: {
          allowedOrigins: [
            'https://portal.azure.com'
            'https://ms.portal.azure.com'
            'https://localhost:53000'
            'http://localhost:53000'
            'http://localhost:3000'
            'https://localhost:3000'
            'https://ashy-river-0fb38b600.7.azurestaticapps.net'
          ]
          allowedMethods: [
            '*'
          ]
          allowedHeaders: [
            '*'
          ]
          allowCredentials: true
        }
      }
      registries: [
        {
          server: acr.properties.loginServer
          username: acr.name
          passwordSecretRef: 'acr-password'
        }
      ]
      secrets: [
        {
          name: 'acr-password'
          value: acrPassword
        }
        {
          name: 'entra-client-secret'
          value: entraClientSecret
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'backend'
          image: image
          env: [
            { name: 'AUTH_METHOD', value: authMethod }
            { name: 'COSMOS_ENDPOINT', value: cosmosEndpoint }
            { name: 'COSMOS_DATABASE', value: databaseName }
            { name: 'CLIENT_ID', value: entraClientId }
            { name: 'CLIENT_SECRET', value: entraClientSecret }
            { name: 'TENANT_ID', value: entraTenantId }
            { name: 'STORAGE_TYPE', value: last(split(storageAccountId, '/')) != '' ? 'blob' : 'filesystem' }
            { name: 'BLOB_STORAGE_ACCOUNT_NAME', value: storageAccountName }
            { name: 'AZURE_STORAGE_CONNECTION_STRING', value: storageConnectionString }
            { name: 'COSMOS_KEY', value: cosmosKey }
            { name: 'AGENT_PACKAGE_CONTAINER', value: 'agent-packages' }
            { name: 'DOWNLOAD_SECRET_KEY', value: uniqueString(resourceGroup().id, acaName, 'download-secret') }
            { name: 'TAB_RESOURCE_DOMAIN', value: tabResourceDomain }
            { name: 'TEAMS_APP_ID', value: teamsAppId }
            { name: 'TENANT_ADMIN_ROLE_ID', value: tenantAdminRoleId }
            { name: 'PRIVILEGED_USER_ROLE_ID', value: privilegedUserRoleId }
            { name: 'PLATFORM_ADMIN_ROLE_ID', value: platformAdminRoleId }
          ]
        }
      ]
    }
  }
}

// 3. EasyAuth 설정 (Authentication)
resource acaAuth 'Microsoft.App/containerApps/authConfigs@2023-05-01' = {
  name: 'current'
  parent: aca
  properties: {
    platform: {
      enabled: false
    }
    globalValidation: {
      unauthenticatedClientAction: 'AllowAnonymous'
      redirectToProvider: 'azureActiveDirectory'
      excludedPaths: [
        '/api/v1/templates/*'
        '/api/v1/packages/download'
        '/api/v1/packages/*'
        '/api/health'
      ]
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: false
        registration: {
          openIdIssuer: '${environment().authentication.loginEndpoint}${empty(entraTenantId) || entraTenantId == 'common' ? 'common' : entraTenantId}/v2.0'
          clientId: entraClientId
          clientSecretSettingName: 'entra-client-secret'
        }
        validation: {
          allowedAudiences: [
            entraClientId
            'api://${entraClientId}'
          ]
        }
      }
    }
  }
}

// --- Managed Identity 권한 할당 ---

// 기존에 배포된 ACR과 Cosmos DB 리소스를 참조
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: last(split(acrId, '/'))
}
resource cosmosAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' existing = {
  name: last(split(cosmosAccountId, '/'))
}

// 3. ACA에 ACR 이미지를 당겨올 권한(AcrPull) 부여
var acrPullRoleDefinitionId = '7f951dda-4ed3-4680-a7ca-43fe172d538d'
resource acrPullRole 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(acr.id, aca.id, acrPullRoleDefinitionId)
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', acrPullRoleDefinitionId)
    principalId: aca.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// 4. ACA에 Cosmos DB 데이터를 읽고 쓸 권한(Data Contributor) 부여
var cosmosDataContributorRole = '00000000-0000-0000-0000-000000000002'
resource sqlRoleAssignment 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2023-04-15' = {
  parent: cosmosAccount
  name: guid(cosmosAccount.id, aca.id, cosmosDataContributorRole)
  properties: {
    roleDefinitionId: '/${subscription().id}/resourceGroups/${resourceGroup().name}/providers/Microsoft.DocumentDB/databaseAccounts/${cosmosAccount.name}/sqlRoleDefinitions/${cosmosDataContributorRole}'
    principalId: aca.identity.principalId
    scope: cosmosAccount.id
  }
}

// 5. ACA에 Blob Storage 데이터를 읽고 쓸 권한(Storage Blob Data Contributor) 부여
var storageBlobDataContributorRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
resource storageRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (storageAccountId != '') {
  name: guid(storageAccountId, aca.id, storageBlobDataContributorRole)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageBlobDataContributorRole)
    principalId: aca.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2023-01-01' existing = if (storageAccountId != '') {
  name: last(split(storageAccountId, '/'))
}

// 6. ACA에 Storage Queue 데이터를 읽고 쓸 권한(Storage Queue Data Contributor) 부여
var storageQueueDataContributorRole = '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
resource queueRoleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (storageAccountId != '') {
  name: guid(storageAccount.id, storageQueueDataContributorRole, aca.id)
  scope: storageAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', storageQueueDataContributorRole)
    principalId: aca.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output acaUrl string = aca.properties.configuration.ingress.fqdn
