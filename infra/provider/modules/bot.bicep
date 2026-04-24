param botName string
param location string = 'global'
param endpoint string
param msaAppId string
param msaAppTenantId string
param msaAppType string = 'SingleTenant'
param sku string = 'F0'

resource bot 'Microsoft.BotService/botServices@2022-09-15' = {
  name: botName
  location: location
  kind: 'azurebot'
  sku: {
    name: sku
  }
  properties: {
    displayName: botName
    endpoint: endpoint
    msaAppId: msaAppId
    msaAppTenantId: msaAppTenantId
    msaAppType: msaAppType
    schemaTransformationVersion: '1.3'
    isStreamingSupported: false
  }
}

// Microsoft Teams Channel 연동
resource teamsChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: bot
  name: 'MsTeamsChannel'
  location: location
  properties: {
    channelName: 'MsTeamsChannel'
    properties: {
      isEnabled: true
    }
  }
}

// Web Chat Channel 연동
resource webChatChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: bot
  name: 'WebChatChannel'
  location: location
  properties: {
    channelName: 'WebChatChannel'
  }
}

// Direct Line Channel 연동 (JSON에 포함되어 있어 추가)
resource directLineChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: bot
  name: 'DirectLineChannel'
  location: location
  properties: {
    channelName: 'DirectLineChannel'
  }
}

output botId string = bot.id
