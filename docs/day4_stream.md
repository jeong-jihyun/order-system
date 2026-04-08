# Day 4 학습 노트 — Java Stream 직접 작성

> 날짜: 2026-04-08 | 주제: Stream API 분석 + 실습

---

## 1. Stream 파이프라인 흐름

```java
orderQueryPort.findAll()         // List<Order>        — 데이터 소스
    .stream()                    // Stream<Order>      — 파이프라인 열기
    .filter(o -> ...)            // Stream<Order>      — 중간 연산: 조건 필터
    .map(OrderResponse::from)    // Stream<OrderResponse> — 중간 연산: 타입 변환
    .sorted(...)                 // Stream<OrderResponse> — 중간 연산: 정렬
    .toList()                    // List<OrderResponse>   — 최종 연산: 수집
```

### 핵심 규칙
- **중간 연산** (`filter`, `map`, `sorted`) — Stream을 반환, 지연 실행(Lazy)
- **최종 연산** (`toList`, `collect`, `reduce`, `count`) — 실제 계산이 발생, 파이프라인 닫힘
- 최종 연산이 없으면 중간 연산은 실행되지 않는다

---

## 2. ⚠️ 가장 중요한 혼동 포인트 — `map()` vs `Map`

| | 설명 | 예시 |
|---|---|---|
| `Stream.map()` | **변환 연산** — 각 요소를 다른 타입으로 1:1 변환 | `.map(Order::getId)` |
| `Map<K,V>` | **자료구조** — key-value 쌍 저장 | `Map<String, Integer>` |

```java
// Stream.map() — Order 하나를 OrderResponse 하나로 변환
stream.map(OrderResponse::from)   // Stream<Order> → Stream<OrderResponse>

// Map<K,V> — 상태별 건수를 담는 자료구조
Map<OrderStatus, Long> result = stream.collect(Collectors.groupingBy(...))
```

---

## 3. 람다 vs 메서드 레퍼런스

코드가 짧아지고 가독성이 좋아진다. 기능은 동일하다.

```java
// 인스턴스 메서드 참조
.map(order -> order.getTotalPrice())   // 람다
.map(Order::getTotalPrice)             // 메서드 레퍼런스

.map(order -> order.getStatus())       // 람다
.map(Order::getStatus)                 // 메서드 레퍼런스

// 정적 메서드 참조
.map(order -> OrderResponse.from(order))  // 람다
.map(OrderResponse::from)                  // 메서드 레퍼런스
```

---

## 4. 정렬 — `sorted()`와 `compareTo` 방향

`sorted()`의 Comparator는 **음수면 a가 앞, 양수면 b가 앞** 규칙을 따른다.

```java
// 오름차순 (작은 값이 앞)
.sorted((a, b) -> a.getTotalPrice().compareTo(b.getTotalPrice()))
// a가 크면 양수 → b가 앞 → 작은 값이 먼저 = 오름차순

// 내림차순 (큰 값이 앞) ← 오늘 작성한 코드
.sorted((a, b) -> b.getTotalPrice().compareTo(a.getTotalPrice()))
// b가 크면 양수 → b가 앞 → 큰 값이 먼저 = 내림차순
```

### 외우는 법
```
b.compareTo(a)  →  B가 먼저(Big first)  →  내림차순 ↓
a.compareTo(b)  →  A가 먼저(Ascending)  →  오름차순 ↑
```

### Comparator 유틸 메서드로 더 읽기 쉽게 작성하기
```java
// 위와 완전히 동일한 결과
.sorted(Comparator.comparing(Order::getTotalPrice).reversed())  // 내림차순
.sorted(Comparator.comparing(Order::getTotalPrice))             // 오름차순
```

---

## 5. 합산 — `reduce()`

```java
public BigDecimal getOrdersTotalAmount() {
    return orderQueryPort.findAll().stream()
            .map(Order::getTotalPrice)          // Stream<BigDecimal>
            .reduce(BigDecimal.ZERO, BigDecimal::add);  // 0부터 시작해서 모두 더함
}
```

- `reduce(초기값, 누적함수)` — 초기값에서 시작해 각 요소를 누적
- `BigDecimal.ZERO` — 초기값 (합산 결과가 0건일 때도 안전하게 0 반환)
- `BigDecimal::add` — `(acc, cur) -> acc.add(cur)` 의 메서드 레퍼런스

---

## 6. 그룹화 — `groupingBy()`

```java
public Map<OrderStatus, Long> getOrderCountByStatus() {
    return orderQueryPort.findAll().stream()
            .collect(Collectors.groupingBy(
                    Order::getStatus,       // 그룹 기준 key
                    Collectors.counting()   // 각 그룹의 집계 방식
            ));
}
```

- `groupingBy(분류함수)` — 분류 함수 결과를 key로 그룹화
- `counting()` — 각 그룹의 요소 수를 Long으로 반환
- 결과 예: `{PENDING=3, COMPLETED=5, CANCELLED=1}`

---

## 7. `.toList()` vs `.collect(Collectors.toList())`

| | `.collect(Collectors.toList())` | `.toList()` |
|---|---|---|
| 도입 버전 | Java 8+ | Java 16+ |
| 결과 | **수정 가능** (add/remove 가능) | **수정 불가** (Unmodifiable) |
| 용도 | 이후에 리스트를 수정해야 할 때 | 조회 전용, 불변 보장 |

```java
List<String> a = stream.collect(Collectors.toList());
a.add("추가");  // ✅ 가능

List<String> b = stream.toList();
b.add("추가");  // ❌ UnsupportedOperationException
```

> **실무 팁:** 조회 서비스에서는 `.toList()` 사용이 더 안전하다 (의도하지 않은 수정 방지)

---

## 8. 오늘 작성한 3개 메서드 전체 코드

```java
// 과제 1: 총 금액 합산
public BigDecimal getOrdersTotalAmount() {
    return orderQueryPort.findAll().stream()
            .map(Order::getTotalPrice)
            .reduce(BigDecimal.ZERO, BigDecimal::add);
}

// 과제 2: 상태별 건수 집계
public Map<OrderStatus, Long> getOrderCountByStatus() {
    return orderQueryPort.findAll().stream()
            .collect(Collectors.groupingBy(
                    Order::getStatus,
                    Collectors.counting()));
}

// 과제 3: PENDING 주문 금액 내림차순 정렬
public List<OrderResponse> getPendingOrdersSortedByPrice() {
    return orderQueryPort.findByStatus(OrderStatus.PENDING).stream()
            .sorted((a, b) -> b.getTotalPrice().compareTo(a.getTotalPrice()))
            .map(OrderResponse::from)
            .collect(Collectors.toList());
}
```

---

## 9. flatMap — 중첩 구조 펼치기

### map() vs flatMap() 핵심 차이

```
map()     : 요소 하나 → 결과 하나    (1 : 1)
flatMap() : 요소 하나 → 결과 여러 개 → 하나로 합침    (1 : N → 평탄화)
```

### 그림으로 이해하기

```
// map() 결과
[[1, 2], [3, 4], [5, 6]]   ← Stream<List<Integer>> 중첩 리스트 그대로

// flatMap() 결과
[1, 2, 3, 4, 5, 6]         ← Stream<Integer> 하나로 평탄화(flatten)
```

### 코드 예시 1 — 기본

```java
List<List<Integer>> nested = List.of(
    List.of(1, 2, 3),
    List.of(4, 5),
    List.of(6, 7, 8, 9)
);

// map() 사용 — Stream<List<Integer>> (중첩 그대로)
nested.stream()
      .map(list -> list.stream())   // Stream<Stream<Integer>>
      .collect(Collectors.toList()) // List<List<Integer>> — 원하는 결과가 아님

// flatMap() 사용 — Stream<Integer> (하나로 합쳐짐)
nested.stream()
      .flatMap(list -> list.stream())  // Stream<Integer>
      .collect(Collectors.toList())    // [1, 2, 3, 4, 5, 6, 7, 8, 9] ✅
```

### 코드 예시 2 — 문자열 분리

```java
List<String> sentences = List.of("Hello World", "Java Stream", "flatMap 예제");

// 각 문장을 단어로 쪼개서 하나의 스트림으로
List<String> words = sentences.stream()
        .flatMap(s -> Arrays.stream(s.split(" ")))  // 각 문장 → String[]
        .collect(Collectors.toList());
// 결과: ["Hello", "World", "Java", "Stream", "flatMap", "예제"]
```

### 코드 예시 3 — 실무 패턴 (주문 → 상품 목록)

```java
// 각 주문(Order)에는 여러 상품(OrderItem)이 있다고 가정
List<Order> orders = orderQueryPort.findAll();

// 전체 주문의 모든 상품 목록을 하나의 리스트로
List<OrderItem> allItems = orders.stream()
        .flatMap(order -> order.getItems().stream())  // Order → Stream<OrderItem>
        .collect(Collectors.toList());

// 응용: 모든 상품명만 추출 (중복 제거)
List<String> productNames = orders.stream()
        .flatMap(order -> order.getItems().stream())
        .map(OrderItem::getProductName)
        .distinct()
        .collect(Collectors.toList());
```

### map() vs flatMap() 선택 기준

| 상황 | 사용 메서드 |
|------|-----------|
| `List<Order>` → `List<OrderResponse>` (1:1 변환) | `map()` |
| `List<Order>` → `List<OrderItem>` (1:N 변환 후 합치기) | `flatMap()` |
| `List<String>` → 각 문자열을 단어로 분리 후 합치기 | `flatMap()` |
| Optional 중첩 제거 (`Optional<Optional<T>>` → `Optional<T>`) | `flatMap()` |

### Optional에서의 flatMap() — 보너스

```java
// map() — Optional<Optional<String>> 중첩 발생
Optional<String> name = Optional.of("hello");
Optional<Optional<String>> bad = name.map(s -> Optional.of(s.toUpperCase()));

// flatMap() — Optional<String> 깔끔하게 반환
Optional<String> good = name.flatMap(s -> Optional.of(s.toUpperCase()));
```

---

## 10. flatMap 실무 시나리오

---

### 시나리오 1 — 쇼핑몰: 주문 목록에서 전체 상품 추출

**상황:** 고객이 여러 주문을 했고, 각 주문에는 여러 상품이 들어있다.  
**목표:** 전체 주문에서 구매한 **모든 상품명 목록**을 중복 없이 뽑아야 한다.

**입력 JSON**
```json
[
  {
    "orderId": 1,
    "customerName": "김철수",
    "items": [
      { "productName": "노트북", "price": 1500000 },
      { "productName": "마우스", "price": 30000 },
      { "productName": "키보드", "price": 80000 }
    ]
  },
  {
    "orderId": 2,
    "customerName": "이영희",
    "items": [
      { "productName": "마우스", "price": 30000 },
      { "productName": "모니터", "price": 400000 }
    ]
  },
  {
    "orderId": 3,
    "customerName": "박민수",
    "items": [
      { "productName": "키보드", "price": 80000 }
    ]
  }
]
```

**Java 코드**
```java
List<String> productNames = orders.stream()
        .flatMap(order -> order.getItems().stream())  // Order → OrderItem (1:N)
        .map(OrderItem::getProductName)               // OrderItem → String
        .distinct()                                   // 중복 제거
        .collect(Collectors.toList());
```

**출력 JSON**
```json
["노트북", "마우스", "키보드", "모니터"]
```

> ✅ `map()`을 쓰면 `[["노트북","마우스","키보드"], ["마우스","모니터"], ["키보드"]]` — 중첩 배열이 된다.

---

### 시나리오 2 — 권한 시스템: 유저 목록에서 전체 권한 집계

**상황:** 각 유저는 여러 역할(Role)을 가지고, 각 역할은 여러 권한(Permission)을 가진다.  
**목표:** 전체 유저가 가진 **모든 권한 목록**을 중복 없이 뽑아야 한다.

**입력 JSON**
```json
[
  {
    "userId": 1,
    "name": "관리자",
    "roles": [
      {
        "roleName": "ADMIN",
        "permissions": ["READ", "WRITE", "DELETE"]
      }
    ]
  },
  {
    "userId": 2,
    "name": "일반유저",
    "roles": [
      {
        "roleName": "USER",
        "permissions": ["READ"]
      },
      {
        "roleName": "EDITOR",
        "permissions": ["READ", "WRITE"]
      }
    ]
  }
]
```

**Java 코드**
```java
List<String> allPermissions = users.stream()
        .flatMap(user -> user.getRoles().stream())          // User → Role (1:N)
        .flatMap(role -> role.getPermissions().stream())    // Role → Permission (1:N)
        .distinct()
        .collect(Collectors.toList());
```

**출력 JSON**
```json
["READ", "WRITE", "DELETE"]
```

> ✅ `flatMap()` 2번 연속 체이닝으로 3단계 중첩 구조(`User → Role → Permission`)를 한 번에 펼친다.

---

### 시나리오 3 — 검색: 여러 키워드로 태그 검색

**상황:** 사용자가 `"Spring Boot Java"` 를 입력하면 태그가 일치하는 게시글을 모두 찾아야 한다.  
**목표:** 각 단어를 분리해 DB에서 각각 조회 후 결과를 하나로 합친다.

**입력값**
```
keyword = "Spring Boot Java"
```

**DB에 저장된 태그 데이터 (각 단어로 조회한 결과)**
```json
"Spring" 검색 → [{ "postId": 1, "title": "Spring 기초" }, { "postId": 2, "title": "Spring Boot 시작" }]
"Boot"   검색 → [{ "postId": 2, "title": "Spring Boot 시작" }, { "postId": 3, "title": "Boot 설정" }]
"Java"   검색 → [{ "postId": 4, "title": "Java 문법" }]
```

**Java 코드**
```java
List<Post> results = Arrays.stream(keyword.split(" "))
        .flatMap(word -> postRepository.findByTag(word).stream())
        .distinct()
        .collect(Collectors.toList());
```

**출력 JSON**
```json
[
  { "postId": 1, "title": "Spring 기초" },
  { "postId": 2, "title": "Spring Boot 시작" },
  { "postId": 3, "title": "Boot 설정" },
  { "postId": 4, "title": "Java 문법" }
]
```

> ✅ `distinct()`가 없으면 `postId: 2` 가 중복으로 2번 나온다.

---

### 시나리오 4 — CSV 파싱: 여러 파일의 데이터를 하나로 합치기

**상황:** 연도별로 분리된 주문 CSV 파일 3개를 합쳐서 전체 주문을 처리해야 한다.

**입력 파일 3개**
```
# orders_2024.csv       # orders_2025.csv       # orders_2026.csv
# 주석 줄               # 주석 줄               # 주석 줄
1,노트북,1500000         3,키보드,80000           5,모니터,400000
2,마우스,30000           4,마우스,30000           6,스피커,150000
```

**Java 코드**
```java
List<String> allLines = csvFiles.stream()
        .flatMap(path -> {
            try {
                return Files.lines(path);
            } catch (IOException e) {
                return Stream.empty();
            }
        })
        .filter(line -> !line.startsWith("#"))  // 주석 줄 제거
        .collect(Collectors.toList());
```

**출력 결과 (List\<String\>)**
```json
[
  "1,노트북,1500000",
  "2,마우스,30000",
  "3,키보드,80000",
  "4,마우스,30000",
  "5,모니터,400000",
  "6,스피커,150000"
]
```

> ✅ 주석 줄(`#`으로 시작)은 `filter()`로 제거됐다.

---

### 시나리오 5 — Optional 체이닝: null 중첩 방지

**상황:** 주문에 배송 정보가 없거나, 배송지 주소가 없을 수 있다.

**입력 JSON — 배송 정보 없음 (null)**
```json
{
  "orderId": 10,
  "customerName": "홍길동",
  "delivery": null
}
```

**출력 결과**
```
"주소 없음"
```

**입력 JSON — 배송 정보 있음**
```json
{
  "orderId": 11,
  "customerName": "홍길동",
  "delivery": {
    "trackingNumber": "123-456",
    "address": {
      "street": "서울시 강남구 테헤란로 123",
      "zipCode": "06234"
    }
  }
}
```

**Java 코드**
```java
String street = Optional.ofNullable(order)
        .flatMap(o -> Optional.ofNullable(o.getDelivery()))
        .flatMap(d -> Optional.ofNullable(d.getAddress()))
        .map(Address::getStreet)
        .orElse("주소 없음");
```

**출력 결과**
```
"서울시 강남구 테헤란로 123"
```

> ✅ 중간에 `null`이 있어도 `NullPointerException` 없이 안전하게 처리된다.

---

### 5가지 시나리오 전체 요약

| 시나리오 | 입력 구조 | 출력 구조 | 핵심 메서드 |
|----------|-----------|-----------|------------|
| 1. 쇼핑몰 상품 추출 | `List<Order { items: [...] }>` | `List<String>` (상품명) | `flatMap + distinct` |
| 2. 권한 집계 | `List<User { roles: [{ permissions: [...] }] }>` | `List<String>` (권한명) | `flatMap x2 + distinct` |
| 3. 키워드 검색 | `String` (공백 구분) | `List<Post>` (중복 제거) | `flatMap + distinct` |
| 4. CSV 파싱 | `List<Path>` (파일 목록) | `List<String>` (전체 줄) | `flatMap + filter` |
| 5. Optional 체이닝 | 중첩 객체 (null 가능) | `String` (또는 기본값) | `Optional.flatMap` |

---

## 11. Stream 중간/최종 연산 치트시트

| 종류 | 메서드 | 설명 |
|------|--------|------|
| 중간 | `filter(Predicate)` | 조건 만족하는 요소만 통과 |
| 중간 | `map(Function)` | 각 요소를 다른 타입으로 변환 (1:1) |
| 중간 | `flatMap(Function)` | 각 요소를 Stream으로 변환 후 하나로 합침 (1:N) |
| 중간 | `sorted(Comparator)` | 정렬 |
| 중간 | `distinct()` | 중복 제거 |
| 중간 | `limit(n)` | 앞에서 n개만 |
| 중간 | `peek(Consumer)` | 디버깅용 중간 확인 |
| 최종 | `toList()` | 불변 List로 수집 (Java 16+) |
| 최종 | `collect(Collectors.toList())` | 가변 List로 수집 |
| 최종 | `collect(Collectors.groupingBy())` | 그룹화 |
| 최종 | `reduce(초기값, 누적함수)` | 단일 값으로 합산 |
| 최종 | `count()` | 요소 수 반환 |
| 최종 | `findFirst()` | 첫 번째 요소 Optional 반환 |
| 최종 | `anyMatch(Predicate)` | 하나라도 조건 만족하면 true |
