param swaName string
param location string

resource staticWebApp 'Microsoft.Web/staticSites@2022-09-01' = {
  name: swaName
  location: location
  sku: {
    name: 'Free'
    tier: 'Free'
  }
  properties: {
    allowConfigFileUpdates: true
    stagingEnvironmentPolicy: 'Enabled'
  }
}

output swaDefaultHostname string = staticWebApp.properties.defaultHostname
output swaId string = staticWebApp.id
