param location string
param lawName string

resource law 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: lawName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

output lawId string = law.id
output customerId string = law.properties.customerId
output sharedKey string = law.listKeys().primarySharedKey
