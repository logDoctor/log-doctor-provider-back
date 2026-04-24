using 'main.bicep'

param env = 'dev'
param acrSku = 'Basic' // 개발용 저렴한 티어
param entraClientId = ''
param image = '' // CLI에서 주입받을 이미지의 기틀
param bootstrapOnly = false
