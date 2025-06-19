# BIPPY MaxScript 바이패드(Biped) 생성 분석 문서

## 개요

BIPPY는 3DS Max에서 FBX 파일의 본(bone) 데이터를 Biped 시스템으로 변환하는 MaxScript 도구입니다. 본 문서는 바이패드를 최초로 생성하는 핵심 메커니즘을 분석합니다.

## 주요 함수

### 1. assess_and_create_biped() 함수
**위치:** 576-703 라인  
**목적:** FBX 본 구조를 분석하여 적절한 Biped를 생성

#### 1.1 바이패드 높이 계산
```maxscript
bip_height = (distance FBX_convert_str.FBX_array[140] FBX_convert_str.FBX_array[13])*1.8
```
- FBX_array[140]: 발목 본 위치
- FBX_array[13]: 목 본 위치
- 두 본 사이의 거리에 1.8을 곱하여 바이패드 전체 높이 결정

#### 1.2 본 구조 분석 및 카운팅

##### 척추(Spine) 본 카운팅
```maxscript
number_of_spines = 0
for c = 3 to 12 do (
    if FBX_convert_str.FBX_array[c] != undefined do(
        number_of_spines += 1
    )
)
```
- 인덱스 3-12: 척추 본들
- 존재하는 척추 본의 개수를 계산

##### 다리(Leg) 본 카운팅
```maxscript
number_of_legs = 0
for c = 137 to 140 do (
    if FBX_convert_str.FBX_array[c] != undefined do(
        number_of_legs += 1
    )
)
```
- 인덱스 137-140: 다리 본들
- 각 다리의 관절 개수 계산

##### 꼬리(Tail) 본 카운팅
```maxscript
number_of_tails = 0
for c = 165 to 189 do (
    if FBX_convert_str.FBX_array[c] != undefined do(
        number_of_tails += 1
    )
)
```

##### 목(Neck) 본 카운팅
```maxscript
number_of_necks = 0
for c = 13 to 37 do (
    if FBX_convert_str.FBX_array[c] != undefined do(
        number_of_necks += 1
    )
)
```

##### 포니테일(Ponytail) 본 카운팅
```maxscript
// 포니테일 1
number_of_ponytails1 = 0
for c = 39 to 63 do (
    if FBX_convert_str.FBX_array[c] != undefined do(
        number_of_ponytails1 += 1
    )
)

// 포니테일 2
number_of_ponytails2 = 0
for c = 64 to 88 do (
    if FBX_convert_str.FBX_array[c] != undefined do(
        number_of_ponytails2 += 1
    )
)
```

##### 손가락(Finger) 본 카운팅
```maxscript
number_of_fingers = 0

// 각 손가락별로 체크 (엄지, 검지, 중지, 약지, 새끼)
if FBX_convert_str.FBX_array[93] != undefined do(
    number_of_fingers += 1
)
// ... (다른 손가락들도 동일한 방식)
```

##### 발가락(Toe) 본 카운팅
```maxscript
number_of_toes = 0
if FBX_convert_str.FBX_array[141] != undefined do(
    number_of_toes += 1
)
// ... (다른 발가락들도 동일한 방식)
```

##### Props 본 체크
```maxscript
number_of_prop1 = false
if FBX_convert_str.FBX_array[200] != undefined do(
    number_of_prop1 = true
)
// Prop2, Prop3도 동일한 방식
```

#### 1.3 바이패드 생성
```maxscript
FBX_convert_str.bipObj = biped.createNew bip_height 0 [0,0,0] \
    spineLinks:number_of_spines \
    legLinks:number_of_legs \
    tailLinks:number_of_tails \
    ponyTail1Links:number_of_ponytails1 \
    neckLinks:number_of_necks \
    ponyTail2Links:number_of_ponytails2 \
    fingers:number_of_fingers \
    fingerLinks:number_of_fingerlinks \
    toes:number_of_toes \
    toeLinks:number_of_toelinks \
    prop1Exists:number_of_prop1 \
    prop2Exists:number_of_prop2 \
    prop3Exists:number_of_prop3
```

이 코드는 3DS Max의 `biped.createNew` 명령을 사용하여:
- 계산된 높이로 바이패드 생성
- 위치: [0,0,0]
- 분석된 본 구조에 맞춰 각 부위별 관절 수 설정

#### 1.4 본 매핑 배열 생성
```maxscript
local file = (getDir #userscripts + "\\Bippy/Bip.btf")
// BTF 파일에서 바이패드 본 이름들을 읽어옴
nam = FBX_convert_str.bipObj.name
FBX_convert_str.retarget_array[1] = FBX_convert_str.bipObj

for bI = 2 to FBX_convert_str.boneNum do(
    name_Temp = "$'"+nam+" "+(readLine fileIO)+"'"
    if FBX_convert_str.FBX_array[bI] != undefined do( 
        FBX_convert_str.retarget_array[bI] = temp = execute(name_Temp)
    )
)
```

### 2. resize_biped() 함수
**위치:** 704-893 라인  
**목적:** 생성된 바이패드를 FBX 본 크기에 맞춰 조정

#### 2.1 Figure Mode 활성화
```maxscript
FBX_convert_str.biped_ctrl = FBX_convert_str.bipObj.transform.controller
FBX_convert_str.biped_ctrl.figureMode = true
```

#### 2.2 각 부위별 크기 조정

##### 루트(Root) 및 펠비스(Pelvis) 조정
```maxscript
-- 루트 본의 위치와 회전 설정
biped.setTransform FBX_convert_str.retarget_array[1] #pos (FBX_convert_str.FBX_array[1].transform.pos) True
biped.setTransform FBX_convert_str.retarget_array[1] #rotation (FBX_convert_str.FBX_array[1].transform.rotation) True

-- 펠비스 크기 조정 (FBX_array[2]는 펠비스, FBX_array[137]은 왼쪽 다리)
local temp = (distance FBX_convert_str.FBX_array[2] FBX_convert_str.FBX_array[137])*2
biped.setTransform FBX_convert_str.retarget_array[2] #scale ([temp,temp,temp]) True
```

##### 척추(Spine) 본 조정
```maxscript
-- 척추 본들 (인덱스 3-12, 최대 10개)
for i = 1 to 10 do(
    if FBX_convert_str.FBX_array[i+2] != undefined do( 
        if FBX_convert_str.FBX_array[i+3] != undefined then (
            -- 다음 척추 본이 있으면 그 사이의 거리 측정
            local temp = distance FBX_convert_str.FBX_array[i+2] FBX_convert_str.FBX_array[i+3]
            biped.setTransform FBX_convert_str.retarget_array[i+2] #scale ([temp,temp,temp]) True
        )else(
            -- 마지막 척추 본이면 목까지의 거리 측정 (FBX_array[13]은 첫 번째 목 본)
            local temp = distance FBX_convert_str.FBX_array[i+2] FBX_convert_str.FBX_array[13]
            biped.setTransform FBX_convert_str.retarget_array[i+2] #scale ([temp,temp,temp]) True
        )
    )
)
```

##### 목(Neck) 본 조정
```maxscript
-- 목 본들 (인덱스 13-37, 최대 25개)
for i = 1 to 25 do(
    if FBX_convert_str.FBX_array[i+12] != undefined do( 
        if FBX_convert_str.FBX_array[i+13] != undefined then (
            -- 다음 목 본이 있으면 그 사이의 거리 측정
            local temp = distance FBX_convert_str.FBX_array[i+12] FBX_convert_str.FBX_array[i+13]
            biped.setTransform FBX_convert_str.retarget_array[i+12] #scale ([temp,temp,temp]) True
        )else(
            -- 마지막 목 본이면 머리까지의 거리 측정 (FBX_array[38]은 머리)
            local temp = distance FBX_convert_str.FBX_array[i+12] FBX_convert_str.FBX_array[38]
            biped.setTransform FBX_convert_str.retarget_array[i+12] #scale ([temp,temp,temp]) True
        )
    )
)
```

##### 포니테일 1 본 조정
```maxscript
-- 첫 번째 포니테일 (인덱스 39-63)
for i = 1 to 25 do(
    if FBX_convert_str.FBX_array[i+38] != undefined do( 
        if (FBX_convert_str.FBX_array[i+39] != undefined) and (FBX_convert_str.FBX_array[i+39].parent == FBX_convert_str.FBX_array[i+38]) then (
            -- 다음 포니테일 본이 있고 부모-자식 관계가 맞으면
            local temp = distance FBX_convert_str.FBX_array[i+38] FBX_convert_str.FBX_array[i+39]
            biped.setTransform FBX_convert_str.retarget_array[i+38] #scale ([temp,temp,temp]) True
        )else(
            -- 그렇지 않으면 이전 본과의 거리 사용
            local temp = distance FBX_convert_str.FBX_array[i+37] FBX_convert_str.FBX_array[i+38]
            biped.setTransform FBX_convert_str.retarget_array[i+38] #scale ([temp,temp,temp]) True
        )
    )
)
```

##### 포니테일 2 본 조정
```maxscript
-- 두 번째 포니테일 (인덱스 64-88)
for i = 1 to 25 do(
    if FBX_convert_str.FBX_array[i+63] != undefined do( 
        if (FBX_convert_str.FBX_array[i+64] != undefined) and (FBX_convert_str.FBX_array[i+64].parent == FBX_convert_str.FBX_array[i+63]) then (
            local temp = distance FBX_convert_str.FBX_array[i+63] FBX_convert_str.FBX_array[i+64]
            biped.setTransform FBX_convert_str.retarget_array[i+63] #scale ([temp,temp,temp]) True
        )else(
            local temp = distance FBX_convert_str.FBX_array[i+62] FBX_convert_str.FBX_array[i+63]
            biped.setTransform FBX_convert_str.retarget_array[i+63] #scale ([temp,temp,temp]) True
        )
    )
)
```

##### 왼쪽 팔(Left Arm) 조정
```maxscript
-- 왼쪽 팔 (인덱스 89-92: 쇄골, 어깨, 팔꿈치, 손목)
for i = 1 to 3 do(
    local temp = distance FBX_convert_str.FBX_array[i+88] FBX_convert_str.FBX_array[i+89]
    biped.setTransform FBX_convert_str.retarget_array[i+88] #scale ([temp,temp,temp]) True
)

-- 왼쪽 손목에서 첫 번째 손가락까지 (있는 경우)
if FBX_convert_str.FBX_array[93] != undefined do( 
    local temp = distance FBX_convert_str.FBX_array[92] FBX_convert_str.FBX_array[93]
    biped.setTransform FBX_convert_str.retarget_array[92] #scale ([temp,temp,temp]) True
)
```

##### 오른쪽 팔(Right Arm) 조정
```maxscript
-- 오른쪽 팔 (인덱스 113-116: 쇄골, 어깨, 팔꿈치, 손목)
for i = 1 to 3 do(
    local temp = distance FBX_convert_str.FBX_array[i+112] FBX_convert_str.FBX_array[i+113]
    biped.setTransform FBX_convert_str.retarget_array[i+112] #scale ([temp,temp,temp]) True
)

-- 오른쪽 손목에서 첫 번째 손가락까지 (있는 경우)
if FBX_convert_str.FBX_array[117] != undefined do( 
    local temp = distance FBX_convert_str.FBX_array[116] FBX_convert_str.FBX_array[117]
    biped.setTransform FBX_convert_str.retarget_array[116] #scale ([temp,temp,temp]) True
)
```

##### 왼쪽 다리(Left Leg) 조정
```maxscript
-- 왼쪽 다리 (인덱스 137-140: 허벅지, 무릎, 발목)
for i = 1 to 3 do(
    if FBX_convert_str.FBX_array[i+136] != undefined do( 
        if FBX_convert_str.FBX_array[i+137] != undefined then (
            -- 다음 다리 본이 있으면 그 사이의 거리
            local temp = distance FBX_convert_str.FBX_array[i+136] FBX_convert_str.FBX_array[i+137]
            biped.setTransform FBX_convert_str.retarget_array[i+136] #scale ([temp,temp,temp]) True
        )else(
            -- 다음 본이 없으면 그 다음 본까지의 거리
            local temp = distance FBX_convert_str.FBX_array[i+136] FBX_convert_str.FBX_array[i+138]
            biped.setTransform FBX_convert_str.retarget_array[i+136] #scale ([temp,temp,temp]) True
        )
    )
)
```

##### 오른쪽 다리(Right Leg) 조정
```maxscript
-- 오른쪽 다리 (인덱스 156-159: 허벅지, 무릎, 발목)
for i = 1 to 3 do(
    if FBX_convert_str.FBX_array[i+155] != undefined do( 
        if FBX_convert_str.FBX_array[i+156] != undefined then (
            local temp = distance FBX_convert_str.FBX_array[i+155] FBX_convert_str.FBX_array[i+156]
            biped.setTransform FBX_convert_str.retarget_array[i+155] #scale ([temp,temp,temp]) True
        )else(
            local temp = distance FBX_convert_str.FBX_array[i+155] FBX_convert_str.FBX_array[i+157]
            biped.setTransform FBX_convert_str.retarget_array[i+155] #scale ([temp,temp,temp]) True
        )
    )
)
```

##### 발 크기 계산 (주석 처리된 코드)
```maxscript
-- 왼쪽 발 크기 계산 예제 (현재는 주석 처리됨)
local a = FBX_convert_str.FBX_array[141].pos  -- 왼쪽 발가락 위치
local b = FBX_convert_str.FBX_array[140].pos  -- 왼쪽 발목 위치
local d = [b.x,b.y,a.z]  -- 발목의 X,Y와 발가락의 Z
local c = [a.x,a.y,b.z]  -- 발가락의 X,Y와 발목의 Z
local lenght = distance c b  -- 발의 길이
local height = distance b d  -- 발의 높이
-- 실제 적용 코드는 주석 처리됨

-- 오른쪽 발도 동일한 방식으로 계산
```

##### 최종 위치 조정
```maxscript
-- 첫 번째 척추 본의 위치를 FBX에 맞춰 재조정
biped.setTransform FBX_convert_str.retarget_array[3] #pos (FBX_convert_str.FBX_array[3].transform.pos) True

-- 모든 바이패드 본의 위치와 회전을 FBX 본에 맞춰 최종 조정
for b = 1 to local_number_of_items do (
    biped.setTransform local_retarget_array[b] #pos (local_fbx_array[b].transform.pos) True
    biped.setTransform local_retarget_array[b] #rotation (local_fbx_array[b].transform.rotation) True
    -- 위치와 회전을 두 번 설정하여 확실하게 적용
    biped.setTransform local_retarget_array[b] #pos (local_fbx_array[b].transform.pos) True
    biped.setTransform local_retarget_array[b] #rotation (local_fbx_array[b].transform.rotation) True
)
```

##### Clavicle과 팔 본들의 위치 조정
BIPPY에서는 Clavicle(쇄골)과 팔 본들에 대한 별도의 위치 조정 루틴은 없습니다. 대신 **모든 본들의 위치와 회전이 일괄적으로 조정**됩니다:

```maxscript
-- 모든 바이패드 본의 위치와 회전을 FBX 본에 맞춰 최종 조정
for b = 1 to local_number_of_items do (
    -- 위치 설정
    biped.setTransform local_retarget_array[b] #pos (local_fbx_array[b].transform.pos) True
    -- 회전 설정  
    biped.setTransform local_retarget_array[b] #rotation (local_fbx_array[b].transform.rotation) True
    -- 안정성을 위해 두 번 설정
    biped.setTransform local_retarget_array[b] #pos (local_fbx_array[b].transform.pos) True
    biped.setTransform local_retarget_array[b] #rotation (local_fbx_array[b].transform.rotation) True
)
```

**Clavicle과 팔 본 인덱스 매핑:**
- **왼쪽 Clavicle**: FBX_array[89] → retarget_array[89]
- **왼쪽 Upper Arm**: FBX_array[90] → retarget_array[90]  
- **왼쪽 Forearm**: FBX_array[91] → retarget_array[91]
- **왼쪽 Hand**: FBX_array[92] → retarget_array[92]
- **오른쪽 Clavicle**: FBX_array[113] → retarget_array[113]
- **오른쪽 Upper Arm**: FBX_array[114] → retarget_array[114]
- **오른쪽 Forearm**: FBX_array[115] → retarget_array[115]
- **오른쪽 Hand**: FBX_array[116] → retarget_array[116]

이 과정에서 Clavicle과 팔 본들도 다른 모든 본들과 동일하게:
1. **크기 조정 단계**: `distance` 함수로 본 간 거리를 측정하여 스케일 설정
2. **위치 조정 단계**: FBX 본의 `transform.pos`를 바이패드 본에 직접 복사
3. **회전 조정 단계**: FBX 본의 `transform.rotation`을 바이패드 본에 직접 복사

##### Figure Mode 해제
```maxscript
-- 크기 조정이 완료되면 Figure Mode 해제
FBX_convert_str.biped_ctrl.figureMode = false
```

**주요 특징:**
- **거리 기반 스케일링**: 각 본 간의 3D 거리를 측정하여 바이패드 본의 스케일 설정
- **조건부 처리**: 본이 존재하지 않는 경우를 대비한 예외 처리
- **부모-자식 관계 확인**: 포니테일과 같은 체인 구조에서 올바른 연결 확인
- **일괄 변환**: 모든 본(Clavicle, 팔, 다리, 척추 등)이 동일한 로직으로 처리
- **이중 설정**: 위치와 회전을 두 번 설정하여 안정적인 적용 보장

### 3. Map_biped_to_FBX() 함수
**위치:** 894 라인 이후  
**목적:** 전체 바이패드 생성 프로세스 관리

#### 3.1 생성 모드 결정
```maxscript
if(FBX_convert_str.using_Own_FIG == false) then (
    assess_and_create_biped()
    resize_biped()    
)
else (
    assess_and_create_biped()
    // FIG 파일 로드 로직
    biped.LoadFigFile FBX_convert_str.biped_ctrl FBX_convert_str.Fig_File
)
```

두 가지 모드:
1. **자동 생성 모드**: FBX 구조 분석하여 자동으로 바이패드 생성
2. **FIG 파일 모드**: 미리 저장된 FIG 파일을 사용하여 바이패드 구조 적용

## FBX 본 인덱스 매핑

| 인덱스 범위 | 본 유형 | 설명 |
|-------------|---------|------|
| 1 | Root | 루트 본 |
| 3-12 | Spine | 척추 본들 |
| 13-37 | Neck | 목 본들 |
| 39-63 | Ponytail1 | 첫 번째 포니테일 |
| 64-88 | Ponytail2 | 두 번째 포니테일 |
| 89-92 | Left Arm | 왼쪽 팔 |
| 93-109 | Left Fingers | 왼쪽 손가락들 |
| 113-116 | Right Arm | 오른쪽 팔 |
| 117-133 | Right Fingers | 오른쪽 손가락들 |
| 137-140 | Left Leg | 왼쪽 다리 |
| 141-153 | Left Toes | 왼쪽 발가락들 |
| 156-159 | Right Leg | 오른쪽 다리 |
| 160-172 | Right Toes | 오른쪽 발가락들 |
| 165-189 | Tail | 꼬리 |
| 200-202 | Props | 프롭 오브젝트들 |

## 생성 프로세스 요약

1. **FBX 본 구조 분석**: 각 부위별 본의 존재 여부와 개수 파악
2. **바이패드 높이 계산**: 발목-목 거리 기반으로 전체 높이 결정
3. **바이패드 생성**: `biped.createNew`로 분석된 구조에 맞는 바이패드 생성
4. **본 매핑**: BTF 파일에서 바이패드 본 이름들을 읽어와 매핑 배열 구성
5. **크기 조정**: Figure Mode에서 각 본의 길이를 FBX 본에 맞춰 조정
6. **애니메이션 적용**: 프레임별로 FBX 본의 transform을 바이패드에 복사

## 주요 특징

- **동적 구조 분석**: FBX 파일의 본 구조를 자동으로 분석하여 적절한 바이패드 생성
- **유연한 매핑**: 다양한 캐릭터 구조(꼬리, 포니테일, 다양한 손가락 수 등)에 대응
- **정확한 크기 조정**: 실제 FBX 본 간의 거리를 측정하여 바이패드 크기 조정
- **배치 처리 지원**: 여러 FBX 파일을 일괄 처리할 수 있는 구조

이 시스템은 모션 캡처 데이터를 3DS Max의 Biped 시스템으로 효율적으로 변환하기 위한 포괄적인 솔루션을 제공합니다. 