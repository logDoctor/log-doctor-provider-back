# 📘 Azure Bicep 초심자 가이드 (문법 vs 내맘대로)

이 가이드는 **Azure가 정해놓은 문법(Syntax)** 과 **여러분이 마음대로 지어도 되는 부분(User Input)** 을 철저히 구분해서 설명합니다.

> 💡 **범례**
>
> - `검은색 코드`: **절대 바꾸면 안 되는** Bicep 문법 키워드입니다.
> - `<이곳>`: **여러분이 직접 작성해야 하는** 부분입니다. (변수명, 값 등)

---

## 1. 리소스 선언 (Resource)

가장 많이 쓰는 기본 형태입니다.

### 📝 공식 (Formula)

```bicep
resource <내맘대로_지은_별명> '<Azure_리소스_타입@버전>' = {
  name: '<Azure에_생성될_실제_이름>'
  location: '<지역_이름>'
  properties: {
    <속성_이름>: <속성_값>
  }
}
```

### 🔍 뜯어보기

1. `resource`: **(문법)** "나 이제 리소스 만든다!"라고 선언하는 키워드. **수정 불가**.
2. `<내맘대로_지은_별명>`: **(내맘대로)** 이 파일 안에서 부를 애칭입니다. (예: `myStorage`, `dbServer`)
3. `'<Azure_리소스_타입@버전>'`: **(Azure 규칙)** 만들고 싶은 자원의 종류입니다. 자동완성이 도와줍니다. (예: `'Microsoft.Storage/storageAccounts@2021-02-01'`)
4. `= { ... }`: **(문법)** 내용을 정의하는 블록입니다.
5. `name:`: **(문법)** 속성 이름입니다. **수정 불가**.
6. `'<Azure에_생성될_실제_이름>'`: **(내맘대로)** 실제 Azure 포털에 뜰 이름입니다. (예: `'logdoctor-st-dev'`)

### ✨ 실제 예시

```bicep
resource stg 'Microsoft.Storage/storageAccounts@2021-02-01' = {
  name: 'uniquestoragename123'
  location: 'koreacentral'
  kind: 'StorageV2'
  sku: {
    name: 'Standard_LRS'
  }
}
```

> `stg`는 내가 지은 별명이고, `uniquestoragename123`은 실제 이름입니다.

---

## 2. 파라미터 (Parameter)

외부에서 값을 주입받고 싶을 때 씁니다.

### 📝 공식

```bicep
param <변수명> <데이터타입> = <기본값>
```

### 🔍 뜯어보기

1. `param`: **(문법)** 파라미터 선언 키워드.
2. `<변수명>`: **(내맘대로)** 코드에서 사용할 변수 이름. (예: `location`, `appName`)
3. `<데이터타입>`: **(문법)** `string`, `int`, `bool`, `array`, `object` 중 하나.
4. `= <기본값>`: **(선택)** 값을 안 넣었을 때 쓸 기본값.

### ✨ 실제 예시

```bicep
param location string = resourceGroup().location
param appName string = 'log-doctor'
```

---

## 3. 변수 (Variable)

복잡한 값을 미리 계산해서 저장해둘 때 씁니다.

### 📝 공식

```bicep
var <변수명> = <값_또는_계산식>
```

### 🔍 뜯어보기

1. `var`: **(문법)** 변수 선언 키워드. (타입을 안 적습니다! 자동으로 추론함)
2. `<변수명>`: **(내맘대로)** 사용할 변수 이름.
3. `<값_또는_계산식>`: **(내맘대로)** 저장할 데이터나 수식.

### ✨ 실제 예시

```bicep
var uniqueStorageName = '${appName}stg${uniqueString(resourceGroup().id)}'
```

> `${ ... }`는 문자열 중간에 변수를 끼워 넣는 **Bicep 문법**입니다.

---

## 4. 출력 (Output)

배포가 끝나고 "이 값은 밖으로 빼줘!"라고 할 때 씁니다. (다른 파일에서 갖다 쓸 수 있음)

### 📝 공식

```bicep
output <내보낼_이름> <데이터타입> = <내보낼_값>
```

### ✨ 실제 예시

```bicep
output storageEndpoint string = stg.properties.primaryEndpoints.blob
```

> `stg`라는 별명을 가진 리소스의 속성(`properties`) 중 `blob` 주소를 `storageEndpoint`라는 이름으로 내보냅니다.

---

## 5. 모듈 (Module) - 다른 파일 불러오기

내가 만든 bicep 파일을 함수처럼 실행합니다.

### 📝 공식

```bicep
module <별명> '<파일_경로>' = {
  name: '<배포_작업_이름>'
  params: {
    <그_파일의_param_이름>: <넘겨줄_값>
  }
}
```

### 🔍 뜯어보기

1. `module`: **(문법)** 모듈 불러오기 키워드.
2. `<별명>`: **(내맘대로)** 이 파일에서 부를 이름.
3. `'<파일_경로>'`: **(내맘대로)** 불러올 bicep 파일 위치. (예: `'./modules/db.bicep'`)
4. `name:`: **(문법)** Azure 배포 기록에 남을 이름.
5. `params:`: **(문법)** 그 파일에 정의된 `param`들에게 값을 넘겨주는 곳.

---

## 🔥 심화 문법 (Advanced)

여기부터는 "좀 치는" 개발자가 되기 위한 문법입니다.

### 6. 반복문 (Loops)

똑같은 리소스를 여러 개 만들 때 씁니다.

```bicep
// [for <반복변수> in <배열>: { ... }]
resource stgs 'Microsoft.Storage/storageAccounts@2021-02-01' = [for i in range(0, 3): {
  name: 'storage${i}'
  ...
}]
```

- `range(0, 3)`: 0, 1, 2 (총 3번) 반복합니다.

### 7. 조건문 (Conditions)

특정 상황(예: 프로덕션 환경)에서만 리소스를 만들고 싶을 때 씁니다.

```bicep
// resource ... = if (<조건식>) { ... }
resource stg 'Microsoft.Storage/storageAccounts@2021-02-01' = if (env == 'prod') {
  name: 'prodstorage'
  ...
}
```

- `env == 'prod'`가 `true`일 때만 생성됩니다. `false`면 무시합니다.

### 8. 기존 리소스 참조 (Existing)

이미 Azure에 만들어져 있는 리소스를 가져와서 정보만 빼올 때 씁니다.

```bicep
resource vnet 'Microsoft.Network/virtualNetworks@2021-02-01' existing = {
  name: 'existing-vnet'
}

output vnetId string = vnet.id
```

- `existing` 키워드를 붙이면 새로 만들지 않고 **조회만** 합니다.

### 9. 스코프 (Scope)

리소스를 어디에 만들지 지정합니다. (기본값은 현재 리소스 그룹)

```bicep
targetScope = 'subscription' // 구독 레벨 배포 (리소스 그룹 만들기 등)
// 또는
targetScope = 'resourceGroup' // (기본값)
```

---

## 💡 요약

- **파란색 키워드 (`resource`, `param`, `var`, `module`, `output`)**: 얘네는 **문법**입니다. 그대로 쓰세요.
- **`=` 왼쪽의 이름들**: 대부분 **여러분이 짓는 이름**입니다. (단, `name:`, `location:` 같은 속성 키워드는 제외)
- **`=` 오른쪽의 값들**: **여러분이 설정하는 값**입니다. (문자열, 숫자, 혹은 다른 변수)
