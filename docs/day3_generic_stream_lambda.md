# Day 3 — Java Generic + Stream + Lambda (2026-04-07)

> 주제: ApiResponse<T> Generic 분석 + OrderService Stream 직접 작성



## 1. Java Generic 핵심 개념

### 선언 위치 2가지

```java
// ① 클래스 레벨 — 인스턴스 생성 시점에 T가 결정됨
public class ApiResponse<T> {
    private final T data;   // 필드에서 T 사용 가능
}

// ② 메서드 레벨 — 메서드 호출 시점에 T가 결정됨 (static 메서드에 필수)
public static <T> ApiResponse<T> success(T data) {
//             ↑ 메서드 자체 T 선언
}
```

**왜 static 메서드에 별도로 `<T>`를 선언하는가?**

- 클래스 레벨 `<T>`는 인스턴스가 있어야 확정됨
- `static` 메서드는 인스턴스 없이 호출되므로 독립적으로 선언 필요



### Generic 타입 규칙

```java
// ✅ 참조 타입만 가능
ApiResponse<String>     — OK
ApiResponse<Integer>    — OK
ApiResponse<Order>      — OK
ApiResponse<List<Order>>— OK (중첩 가능)
ApiResponse<Void>       — OK (반환값 없을 때)

// ❌ Primitive 타입 불가
ApiResponse<int>        — 컴파일 에러
ApiResponse<double>     — 컴파일 에러
ApiResponse<boolean>    — 컴파일 에러
```

**Primitive → Wrapper 클래스 대응표:**

| Primitive | Wrapper | Auto-boxing |
|-----------|---------|-------------|
| `int` | `Integer` | `Integer i = 42;` (자동 변환) |
| `long` | `Long` | `Long l = 100L;` |
| `double` | `Double` | `Double d = 3.14;` |
| `boolean` | `Boolean` | `Boolean b = true;` |



### Bounded Wildcard — 타입 범위 제한

```java
// T는 Number의 하위 타입만 허용 (Integer, Double, BigDecimal 등)
public static <T extends Number> double sum(List<T> list) {
    return list.stream()
               .mapToDouble(Number::doubleValue)
               .sum();
}

// 호출 예
sum(List.of(1, 2, 3))              // → 6.0
sum(List.of(1.5, 2.5))            // → 4.0
sum(List.of(new BigDecimal("10"))) // → 10.0
sum(List.of("a", "b"))            // ❌ 컴파일 에러 — String은 Number 아님
```



**Wildcard 종류:**

```java
<T extends 상위타입>   // 상위타입 포함 하위 타입만 허용 (Upper Bounded)
<T super 하위타입>     // 하위타입 포함 상위 타입만 허용 (Lower Bounded)
<?>                   // 모든 타입 허용 (Unbounded)
```



### 오늘 작성한 코드

```java
// ApiResponse.java에 추가
public static <T extends Number> double sum(List<T> list) {
    return list.stream()
               .mapToDouble(Number::doubleValue)
               .sum();
}
```



## 2. Java Stream — 핵심 개념

### Stream이란?

컬렉션(List, Set 등)의 요소를 **선언적으로 처리**하는 API  
for문 없이 filter/map/collect 체이닝으로 데이터를 가공

```java
// for문 방식 (명령형)
List<OrderResponse> result = new ArrayList<>();
for (Order order : orders) {
    if (order.getStatus() == OrderStatus.PENDING) {
        result.add(OrderResponse.from(order));
    }
}

// Stream 방식 (선언형) — 같은 결과
List<OrderResponse> result = orders.stream()
    .filter(order -> order.getStatus() == OrderStatus.PENDING)
    .map(OrderResponse::from)
    .collect(Collectors.toList());
```



### Stream 3단계 구조

```
[데이터 소스] → [중간 연산] → [최종 연산]
  List, Set      filter, map    collect, count
  Array          sorted         forEach, reduce
  Stream.of()    distinct       findFirst, anyMatch
```



### 중간 연산 (Intermediate Operations) — 지연 실행(Lazy)

중간 연산은 **최종 연산이 호출될 때까지 실행되지 않습니다.**

```java
// filter — 조건에 맞는 요소만 통과
.filter(order -> order.getStatus() == OrderStatus.PENDING)
.filter(order -> order.getTotalPrice().compareTo(BigDecimal.ZERO) > 0)

// map — 요소를 다른 형태로 변환
.map(OrderResponse::from)          // Order → OrderResponse
.map(order -> order.getId())       // Order → Long
.map(String::toUpperCase)          // String → String (대문자)

// mapToInt / mapToDouble / mapToLong — 숫자 스트림으로 변환
.mapToInt(Order::getQuantity)      // IntStream (sum, avg 등 사용 가능)
.mapToDouble(Number::doubleValue)  // DoubleStream

// flatMap — 중첩 컬렉션을 평탄화
List<List<Order>> nested = ...;
nested.stream()
    .flatMap(List::stream)         // List<List<Order>> → Stream<Order>
    .collect(Collectors.toList());

// sorted — 정렬
.sorted()                                           // 자연 정렬
.sorted(Comparator.comparing(Order::getTotalPrice)) // 가격 오름차순
.sorted(Comparator.comparing(Order::getTotalPrice).reversed()) // 내림차순

// distinct — 중복 제거
.distinct()

// limit / skip — 개수 제한 / 건너뛰기
.limit(10)    // 처음 10개만
.skip(5)      // 처음 5개 건너뜀

// peek — 중간에 값 확인 (디버깅용)
.peek(order -> log.debug("Processing: {}", order.getId()))
```



### 최종 연산 (Terminal Operations) — 실제 실행

```java
// collect — 수집
.collect(Collectors.toList())           // → List
.collect(Collectors.toSet())            // → Set
.collect(Collectors.toUnmodifiableList()) // → 불변 List (Java 10+)

// count — 개수
long count = orders.stream()
    .filter(o -> o.getStatus() == PENDING)
    .count();

// sum / average / max / min (숫자 스트림)
int totalQuantity = orders.stream()
    .mapToInt(Order::getQuantity)
    .sum();

OptionalDouble avg = orders.stream()
    .mapToDouble(o -> o.getTotalPrice().doubleValue())
    .average();

// reduce — 누적 연산
Optional<BigDecimal> total = orders.stream()
    .map(Order::getTotalPrice)
    .reduce(BigDecimal::add);

// forEach — 각 요소 처리 (반환값 없음)
orders.stream()
    .forEach(order -> System.out.println(order.getId()));

// findFirst / findAny — 첫 번째 요소
Optional<Order> first = orders.stream()
    .filter(o -> o.getStatus() == PENDING)
    .findFirst();

// anyMatch / allMatch / noneMatch — 조건 검사
boolean hasPending = orders.stream()
    .anyMatch(o -> o.getStatus() == PENDING);   // 하나라도 PENDING?

boolean allPending = orders.stream()
    .allMatch(o -> o.getStatus() == PENDING);   // 전부 PENDING?

boolean nonePending = orders.stream()
    .noneMatch(o -> o.getStatus() == PENDING);  // PENDING 없음?
```



### Collectors 심화

```java
// groupingBy — 그룹핑
Map<OrderStatus, List<Order>> grouped = orders.stream()
    .collect(Collectors.groupingBy(Order::getStatus));

// groupingBy + counting — 상태별 건수
Map<OrderStatus, Long> countByStatus = orders.stream()
    .collect(Collectors.groupingBy(Order::getStatus, Collectors.counting()));

// joining — 문자열 합치기
String names = orders.stream()
    .map(Order::getCustomerName)
    .collect(Collectors.joining(", "));
// → "홍길동, 김철수, 이영희"

// toMap — Map으로 수집
Map<Long, OrderResponse> orderMap = orders.stream()
    .collect(Collectors.toMap(
        Order::getId,              // key
        OrderResponse::from        // value
    ));

// partitioningBy — 조건으로 두 그룹 분리
Map<Boolean, List<Order>> partitioned = orders.stream()
    .collect(Collectors.partitioningBy(
        o -> o.getStatus() == PENDING
    ));
// partitioned.get(true)  → PENDING 목록
// partitioned.get(false) → 나머지 목록
```



## 3. Lambda 표현식

### 기본 문법

```java
// 전통적인 익명 클래스
Comparator<Order> comp = new Comparator<Order>() {
    @Override
    public int compare(Order a, Order b) {
        return a.getId().compareTo(b.getId());
    }
};

// 람다로 축약
Comparator<Order> comp = (a, b) -> a.getId().compareTo(b.getId());

// 파라미터 1개 — 괄호 생략 가능
.filter(order -> order.getStatus() == PENDING)

// 파라미터 0개
Runnable r = () -> System.out.println("실행");

// 본문 여러 줄 — 중괄호 + return 필요
.map(order -> {
    log.debug("변환: {}", order.getId());
    return OrderResponse.from(order);
})
```



### 메서드 레퍼런스 4가지

```java
// ① 정적 메서드 참조: 클래스::정적메서드
.map(String::valueOf)                // n -> String.valueOf(n)

// ② 인스턴스 메서드 참조 (특정 인스턴스): 인스턴스::메서드
orderEventProducer::sendOrderEvent   // event -> orderEventProducer.sendOrderEvent(event)

// ③ 인스턴스 메서드 참조 (임의 인스턴스): 클래스::메서드
.map(Order::getCustomerName)         // order -> order.getCustomerName()
.map(OrderResponse::from)            // order -> OrderResponse.from(order)

// ④ 생성자 참조: 클래스::new
.map(Order::new)                     // data -> new Order(data)
```



### 함수형 인터페이스 (Functional Interface)

람다는 **추상 메서드가 1개**인 인터페이스에만 사용 가능

| 인터페이스 | 메서드 | 용도 |
|-----------|--------|------|
| `Predicate<T>` | `boolean test(T t)` | filter 조건 |
| `Function<T,R>` | `R apply(T t)` | map 변환 |
| `Consumer<T>` | `void accept(T t)` | forEach 처리 |
| `Supplier<T>` | `T get()` | 값 공급 |
| `BiFunction<T,U,R>` | `R apply(T t, U u)` | 파라미터 2개 변환 |
| `Comparator<T>` | `int compare(T o1, T o2)` | 정렬 |

```java
// Predicate 활용
Predicate<Order> isPending = order -> order.getStatus() == PENDING;
Predicate<Order> isHighPrice = order -> order.getTotalPrice().compareTo(new BigDecimal("10000")) > 0;

orders.stream()
    .filter(isPending.and(isHighPrice))   // AND 조합
    .collect(Collectors.toList());

orders.stream()
    .filter(isPending.or(isHighPrice))    // OR 조합
    .collect(Collectors.toList());

orders.stream()
    .filter(isPending.negate())           // NOT
    .collect(Collectors.toList());
```



## 4. 오늘 직접 작성한 코드

### ApiResponse.java — Bounded Generic

```java
public static <T extends Number> double sum(List<T> list) {
    return list.stream()
               .mapToDouble(Number::doubleValue)
               .sum();
}
```



### OrderService.java — Stream filter 추가

```java
// PENDING 주문만 조회 (Stream filter 실습)
public List<OrderResponse> getPendingOrders() {
    return orderRepository.findAll().stream()
            .filter(order -> order.getStatus() == OrderStatus.PENDING)
            .map(OrderResponse::from)
            .collect(Collectors.toList());
}
```



## 5. 실무에서 자주 쓰는 Stream 패턴

```java
// ① ID → 엔티티 Map 만들기
Map<Long, Order> orderMap = orders.stream()
    .collect(Collectors.toMap(Order::getId, Function.identity()));

// ② null 안전한 스트림 (NullPointerException 방지)
Optional.ofNullable(orders)
    .orElse(Collections.emptyList())
    .stream()
    .filter(...)

// ③ 페이징 처리 (DB 없이 Java에서)
List<Order> page = orders.stream()
    .skip((pageNumber - 1) * pageSize)  // offset
    .limit(pageSize)                     // limit
    .collect(Collectors.toList());

// ④ 최댓값/최솟값 찾기
Optional<Order> mostExpensive = orders.stream()
    .max(Comparator.comparing(Order::getTotalPrice));

// ⑤ 특정 필드만 추출
List<Long> ids = orders.stream()
    .map(Order::getId)
    .collect(Collectors.toList());

// ⑥ 조건 만족하는 최초 요소
Optional<Order> firstPending = orders.stream()
    .filter(o -> o.getStatus() == PENDING)
    .findFirst();
firstPending.ifPresent(o -> log.info("첫 PENDING: {}", o.getId()));
```



## 6. Optional — NullPointerException 방지

Stream과 함께 자주 쓰이는 Optional

```java
// orElseThrow — 없으면 예외 (현재 OrderService 방식)
Order order = orderRepository.findById(id)
    .orElseThrow(() -> new IllegalArgumentException("주문 없음"));

// orElse — 없으면 기본값
Order order = orderRepository.findById(id)
    .orElse(new Order());

// orElseGet — 없으면 공급자 실행 (lazy)
Order order = orderRepository.findById(id)
    .orElseGet(() -> createDefaultOrder());

// map — Optional 안의 값 변환
Optional<String> name = orderRepository.findById(id)
    .map(Order::getCustomerName);

// ifPresent — 값이 있을 때만 실행
orderRepository.findById(id)
    .ifPresent(order -> log.info("조회됨: {}", order.getId()));
```



## 7. 개발 팁

### Stream vs for문 선택 기준

| 상황 | 권장 |
|------|------|
| 단순 변환/필터링 | Stream |
| 중간에 예외 처리 필요 | for문 or try-catch 래핑 |
| 인덱스가 필요한 경우 | for문 |
| 가독성이 중요한 복잡 로직 | 명명된 메서드로 추출 후 Stream |
| 성능이 극도로 중요 | 벤치마크 후 결정 |



### `Collectors.toList()` vs `Stream.toList()` (Java 16+)

```java
.collect(Collectors.toList()) // 변경 가능한 List
.toList()                     // 불변 List (Java 16+, 더 간결)
```



### DB 필터링 vs Java Stream 필터링

```java
// ✅ 실무 권장 — DB에서 필터링 (인덱스 활용)
orderRepository.findByStatus(PENDING)

// ⚠️ 학습/소규모용 — Java에서 필터링 (전체 조회 후 필터)
orderRepository.findAll().stream()
    .filter(o -> o.getStatus() == PENDING)
```



## 8. 참고 자료

| 주제 | URL |
|------|-----|
| Java Generic 공식 튜토리얼 | https://docs.oracle.com/javase/tutorial/java/generics/ |
| Java Stream API 문서 | https://docs.oracle.com/en/java/docs/api/java.base/java/util/stream/Stream.html |
| Java Collectors 문서 | https://docs.oracle.com/en/java/docs/api/java.base/java/util/stream/Collectors.html |
| Baeldung — Java Stream | https://www.baeldung.com/java-8-streams |
| Baeldung — Java Generic | https://www.baeldung.com/java-generics |
| Baeldung — Lambda | https://www.baeldung.com/java-8-lambda-expressions-tips |
| Baeldung — Optional | https://www.baeldung.com/java-optional |
