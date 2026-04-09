# Day 6 학습 노트 — Week 1 복습 + 직접 설명하기

> 날짜: 2026-04-09 | 주제: Generic/Stream 구술 복습 + docker-compose 재현

---

## 1교시 — Generic + Stream 복습 (코드 없이 설명)

---

### Q1. Generic이 왜 필요한가?

**핵심: 타입 안전성 + 편의성 동시에 얻기**

```java
// Generic 없음 — 런타임에 터짐
List list = new ArrayList();
list.add("문자열");
list.add(123);
String s = (String) list.get(1); // ClassCastException 💥

// Generic 있음 — 컴파일 시점에 잡힘
List<String> list = new ArrayList<>();
list.add(123); // 컴파일 에러 ✅
String s = list.get(0); // 캐스팅 불필요
```

**잘못된 이해 → 수정:**
> ❌ "타입 제약을 받지 않고 유연하게" — 이것은 Generic 없을 때의 특징  
> ✅ "어떤 타입이든 쓸 수 있되, 어떤 타입인지 컴파일러가 알게 해서 실수를 미리 막는 것"

---

### Q2. Stream vs for문 차이

**구조 차이:**
```
for문:   초기화 → 조건 → 후처리  (명령형 — How)
Stream:  생성 → 중간연산 → 최종연산  (선언형 — What)
```

**선언형 vs 명령형:**
```java
// for문 — 어떻게(How): i를 증가시키며 조건 검사
List<String> result = new ArrayList<>();
for (int i = 0; i < orders.size(); i++) {
    if (orders.get(i).getStatus().equals("PENDING")) {
        result.add(orders.get(i).getCustomerName());
    }
}

// Stream — 무엇을(What): PENDING인 것을 골라 이름만 모아라
List<String> result = orders.stream()
    .filter(o -> o.getStatus().equals("PENDING"))
    .map(Order::getCustomerName)
    .collect(Collectors.toList());
```

**Stream만의 특징:**
- **지연 평가(Lazy)** — 최종 연산(`collect`, `count`)이 호출되기 전까지 중간 연산은 실행 안 됨
- **병렬 처리** — `.parallelStream()`으로 멀티코어 활용 (for문은 직접 스레드 관리 필요)

---

### Q3. map() vs flatMap()

**map — 1:1 변환**
```
[주문1, 주문2, 주문3]
    ↓ map(주문 → 고객명)
["홍길동", "이순신", "강감찬"]   // 개수 동일
```

**flatMap이 필요한 순간 — 결과가 List인 경우**
```
[주문1, 주문2]
    ↓ map(주문 → 상품목록)
[["사과","배"], ["딸기"]]        // Stream<List<String>> → 쓰기 불편

    ↓ flatMap(주문 → 상품목록.stream())
["사과", "배", "딸기"]           // Stream<String> — 한 줄로 펼쳐짐
```

| | 입력 | 출력 |
|--|------|------|
| `map` | 요소 1개 | 값 1개 (1:1) |
| `flatMap` | 요소 1개 | Stream (1:N) → 펼침 |

> `flatMap` = `map` + 중첩 제거 — "리스트의 리스트"를 "하나의 리스트"로

---

### Q4. Collectors.groupingBy() 결과

**반환 타입: `Map<K, List<V>>`**

```java
Map<OrderStatus, List<Order>> result = orders.stream()
    .collect(Collectors.groupingBy(Order::getStatus));

// 결과
{
  PENDING → [주문A, 주문C],
  FILLED  → [주문B, 주문D]
}
```

**downstream collector로 값도 변환:**
```java
// 개수 집계
Map<OrderStatus, Long> count = orders.stream()
    .collect(Collectors.groupingBy(
        Order::getStatus,
        Collectors.counting()   // List<Order> 대신 Long
    ));
// { PENDING=2, FILLED=2 }
```

> `groupingBy()` = SQL의 `GROUP BY` — 항상 `Map<기준, List<요소>>`

---

### Q5. reduce(0, Integer::sum) 의 0은?

**이름: `identity` (항등값)**

> `identity + 어떤 값 = 어떤 값` 이 항상 성립
```
덧셈 항등값 = 0   →   0 + 5 = 5  ✅
곱셈 항등값 = 1   →   1 × 5 = 5  ✅
```

**동작 순서:**
```
[10, 20, 30].stream().reduce(0, Integer::sum)

0  + 10 = 10   ← identity가 첫 번째 누적값
10 + 20 = 30
30 + 30 = 60   ← 최종 결과
```

**identity 유무 차이:**
```java
List<Integer> empty = List.of();

empty.stream().reduce(0, Integer::sum);  // → 0 (int 반환)
empty.stream().reduce(Integer::sum);     // → Optional.empty() (Optional<Integer> 반환)
```

---

## 2교시 — docker-compose 직접 재현

연습 파일: [docs/practice_docker_compose.yml](practice_docker_compose.yml)

---

### 작성한 내용과 실제 비교

**✅ 정확하게 작성한 부분:**
- `build.context` + `dockerfile` 구조
- `ports: "8081:8081"`
- `SPRING_DATA_REDIS_HOST/PORT`, `SPRING_KAFKA_BOOTSTRAP_SERVERS`
- `depends_on` 구조

**🔧 실제와 달랐던 부분 3가지:**

**1. 공통 Dockerfile + args 구조**
```yaml
# 작성한 것 (서비스별 Dockerfile)
build:
  context: ./services/order-service
  dockerfile: Dockerfile

# 실제 (공통 Dockerfile, args로 서비스 구분)
build:
  context: .
  dockerfile: docker/Dockerfile
  args:
    SERVICE_DIR: order-service
    JAR_NAME: order-service
```
→ 모든 서비스가 하나의 Dockerfile을 공유 — 빌드 파일 중복 제거

**2. `container_name` + `networks` 누락**
```yaml
container_name: exchange-order-service
networks:
  - exchange-net
```
→ `networks`: 서비스 간 같은 네트워크에 있어야 서로 hostname으로 통신 가능

**3. `depends_on` 에 `condition` 조건**
```yaml
# 작성한 것
depends_on:
  - exchange-mysql

# 실제
depends_on:
  mysql:
    condition: service_healthy
```

---

### 핵심 개념: `condition: service_healthy`

| 조건 | 의미 |
|------|------|
| (없음) | 의존 컨테이너 **프로세스가 시작됨** |
| `service_started` | 위와 동일 |
| `service_healthy` | 의존 컨테이너의 **healthcheck가 통과됨** |
| `service_completed_successfully` | 의존 컨테이너가 **정상 종료됨** (init 컨테이너 용) |

**`service_healthy` 없을 때 발생하는 버그:**
```
MySQL 컨테이너 시작 (프로세스 기동)
    ↓ depends_on 조건 충족 → order-service 시작
    ↓ MySQL이 아직 초기화 중
    ↓ Spring Boot DB 연결 시도 → 실패 💥
```

**`service_healthy` 있을 때:**
```
MySQL 컨테이너 healthcheck 통과 (쿼리 가능 상태)
    ↓ 조건 충족 → order-service 시작
    ↓ DB 연결 성공 ✅
```

healthcheck는 이렇게 설정:
```yaml
mysql:
  healthcheck:
    test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]
    interval: 10s
    timeout: 5s
    retries: 5
```

---

## 핵심 정리

| 개념 | 한 줄 요약 |
|------|----------|
| Generic | 유연성 + 타입 안전성 동시. 컴파일 시점에 오류 차단 |
| Stream vs for | 선언형(What) vs 명령형(How). Lazy + 병렬 처리 가능 |
| flatMap | 1:N 변환 후 중첩 제거. "리스트의 리스트 → 하나의 리스트" |
| groupingBy | `Map<K, List<V>>` = SQL GROUP BY |
| reduce identity | 항등값. 빈 Stream 시 기본값 역할 |
| docker args | 공통 Dockerfile을 args로 서비스 구분 → 파일 중복 제거 |
| service_healthy | 프로세스 시작 ≠ 서비스 준비. DB healthcheck 통과 후 시작해야 안전 |
