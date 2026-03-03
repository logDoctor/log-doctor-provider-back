// Microsoft Graph 확장을 사용하겠다고 선언 (Entra ID 제어용)
extension 'br:mcr.microsoft.com/bicep/extensions/microsoftgraph/v1.0:1.0.0'

param appDisplayName string = 'Log Doctor App'
param replyUrl string // ACA 배포 후 발급받은 URL을 주입받음

// 1. Entra ID App Registration (앱 등록) 생성
resource entraApp 'Microsoft.Graph/applications@v1.0' = {
  uniqueName: 'log-doctor-${uniqueString(resourceGroup().id)}'
  displayName: appDisplayName
  // ★ 여기가 핵심입니다! 이 설정으로 '멀티 테넌트' 앱이 됩니다.
  signInAudience: 'AzureADMultipleOrgs' 
  web: {
    redirectUris: [
      '${replyUrl}/api/v1/auth/callback' // 백엔드 콜백 URL
    ]
    implicitGrantSettings: {
      enableIdTokenIssuance: true
      enableAccessTokenIssuance: true
    }
  }
  // 향후 MS Teams 연동이나 OBO 흐름에 필요한 API 권한(Scope)도 여기서 코드로 미리 정의할 수 있습니다.
  api: {
    requestedAccessTokenVersion: 2
  }
}

// 2. Service Principal 생성 (Enterprise Application 목록에 등록하기 위함)
resource servicePrincipal 'Microsoft.Graph/servicePrincipals@v1.0' = {
  appId: entraApp.appId
}

// 3. 백엔드 앱(ACA)에 주입하기 위해 Client ID 반환
output clientId string = entraApp.appId
