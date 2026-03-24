// 구독 레벨 역할 할당 모듈
// Bicep이 인라인 리소스를 nested deployment로 래핑할 때 발생하는
// apiVersion/location 호환성 문제를 회피하기 위해 별도 모듈로 분리합니다.

targetScope = 'subscription'

@description('역할을 할당할 서비스 주체의 Object ID')
param principalId string

@description('할당할 역할 정의의 리소스 ID')
param roleDefinitionId string

@description('역할 할당에 사용할 고유 이름 시드')
param roleAssignmentSeed string

resource roleAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, principalId, roleDefinitionId, roleAssignmentSeed)
  properties: {
    roleDefinitionId: roleDefinitionId
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
