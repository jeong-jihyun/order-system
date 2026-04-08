# OrderCommandService — CQRS Command 측 전체 흐름 분석

> 파일 경로: `services/order-service/src/main/java/com/exchange/order/domain/order/service/command/OrderCommandService.java`
> 분석 날짜: 2026-04-08

---

## 1. 이 클래스의 역할 — 한 줄 요약

> **주문 생성/수정/삭제에 관한 모든 "결과를 바꾸는 작업"을 처리하는 CQRS Command 핸들러**

읽기(`findById`, `findAll`)는 `OrderQueryService`가 담당 → 이 클래스는 **쓰기만**.

---

## 2. 클래스 레벨 구조

```java
@Slf4j
@Service
@RequiredArgsConstructor  // final 필드 → 생성자 주입 자동 생성 (Lombok)
@Transactional            // 모든 메서드 기본 트랜잭션 적용
public class OrderCommandService {

    private final OrderCommandPort orderCommandPort;      // DB 저장/삭제
    private final OrderQueryPort orderQueryPort;          // 조회 (취소 시 필요)
    private final OrderStrategyFactory strategyFactory;   // 전략 패턴 팩토리
    private final OrderValidator orderValidator;          // 공통 검증
    private final ApplicationEventPublisher eventPublisher; // Spring 도메인 이벤트
    private final OutboxService outboxService;            // Outbox 패턴
    private final AccountServiceClient accountServiceClient; // 증거금 동결/해제
}
```

### 주입된 의존성 역할 요약

| 의존성 | 역할 | 계층 |
|--------|------|------|
| `OrderCommandPort` | DB 저장/삭제 인터페이스 | Domain (Port) |
| `OrderQueryPort` | 주문 조회 인터페이스 | Domain (Port) |
| `OrderStrategyFactory` | 주문 타입별 전략 선택 | Domain (Strategy) |
| `OrderValidator` | 공통 유효성 검증 체인 | Domain |
| `ApplicationEventPublisher` | Spring 내부 이벤트 발행 | Infrastructure |
| `OutboxService` | DB에 이벤트 먼저 저장 | Domain (Outbox) |
| `AccountServiceClient` | account-service REST 호출 | Infrastructure (Client) |

---

## 3. createOrder() — 주문 생성 단계별 분해

```java
public OrderResponse createOrder(OrderRequest request) {
```

### Step 1 — 공통 검증 (`OrderValidator`)

```java
orderValidator.validate(request);
```

`OrderValidator`는 `@FunctionalInterface`:

```java
@FunctionalInterface
public interface OrderValidator {
    void validate(OrderRequest request);

    default OrderValidator andThen(OrderValidator next) {
        return request -> {
            this.validate(request);
            next.validate(request);
        };
    }
}
```

- `andThen()`으로 검증 체인 구성 가능
- 예: `nullCheck.andThen(rangeCheck).andThen(businessRule)` 형태로 조합
- 함수형 인터페이스 → **단위 테스트 시 람다로 모킹 가능**

```java
// 테스트 예시
OrderValidator alwaysPass = request -> {};
OrderValidator alwaysFail = request -> { throw new Exception("실패"); };
```

---

### Step 2 — 전략 선택 (`Strategy 패턴`)

```java
OrderType orderType = request.getOrderType() != null ? request.getOrderType() : OrderType.LIMIT;
OrderStrategy strategy = strategyFactory.getStrategy(orderType);
strategy.validate(request);   // 타입별 필드 검증
strategy.preProcess(request); // 타입별 전처리 (선택)
```

**전략별 validate() 차이:**

| 전략 | 검증 내용 |
|------|----------|
| `LimitOrderStrategy` | `totalPrice` 필수 |
| `MarketOrderStrategy` | `totalPrice` 없어도 됨 |
| `StopLossOrderStrategy` | `stopPrice` 필수 |
| `StopLimitOrderStrategy` | `stopPrice` + `totalPrice` 모두 필수 |

→ `OrderCommandService`는 어떤 전략인지 **모름** — `OrderStrategy` 인터페이스만 호출

---

### Step 3 — 매수 증거금 동결 (`AccountServiceClient`)

```java
BigDecimal orderAmount = request.getTotalPrice()
        .multiply(BigDecimal.valueOf(request.getQuantity()));

if ("BUY".equalsIgnoreCase(side)) {
    boolean frozen = accountServiceClient.freezeBalance(request.getCustomerName(), orderAmount);
    if (!frozen) {
        throw new IllegalStateException("잔고가 부족합니다. 증거금 동결 실패.");
    }
}
```

**흐름:**
```
orderAmount = price × quantity   // 주문 총액 계산
        ↓
account-service POST /api/v1/accounts/freeze   // REST 호출
        ↓
잔고 부족 또는 서버 오류 → false 반환 → IllegalStateException (주문 거부)
```

**왜 SELL은 동결하지 않나?**
- 매도는 이미 보유한 수량을 파는 것 → 현금이 필요 없음
- 매도 후 현금 입금은 정산(settlement) 단계에서 처리됨

---

### Step 4 — 주문 DB 저장

```java
Order order = Order.builder()
        .customerName(request.getCustomerName())
        ...
        .status(OrderStatus.PENDING) // 항상 PENDING으로 시작
        .build();
Order savedOrder = orderCommandPort.save(order);
```

- `@Builder` 빌더 패턴으로 객체 생성 → 필드 이름이 명확하게 드러남
- `PENDING` 상태로 고정 — 거래소(trading-engine)가 처리해야 `FILLED`가 됨

**OrderCommandPort — 인터페이스(포트)**

```java
public interface OrderCommandPort {
    Order save(Order order);
    void deleteById(Long id);
}
```

- 실제 JPA 구현체는 Adapter 계층에 있음
- `OrderCommandService`는 JPA를 직접 모름 → 테스트 시 인메모리 구현으로 교체 가능

---

### Step 5 — Outbox 이벤트 저장 (같은 트랜잭션)

```java
HashMap<String, Object> payload = new HashMap<>();
payload.put("orderId", savedOrder.getId());
payload.put("customerName", savedOrder.getCustomerName());
// ...
outboxService.save("Order", savedOrder.getId(),
        "ORDER_CREATED", KafkaConfig.ORDER_TOPIC, payload);
```

**왜 Outbox를 쓰는가?**

```
❌ 기존 방식 (위험)
주문 DB 저장 ─ 성공
Kafka 직접 발행 ─ 네트워크 오류 → 이벤트 소실 → 거래소가 주문을 모름

✅ Outbox 방식 (안전)
주문 DB 저장  ┐
outbox 행 저장 ┘ ← 단일 트랜잭션 (DB 커밋 = 이벤트 반드시 존재)
         ↓
OutboxEventPublisher (스케줄러 5초마다)
         ↓
Kafka 발행 성공 → outbox.status = PUBLISHED
Kafka 발행 실패 → retryCount++ (최대 5회 재시도 → DEAD_LETTER)
```

**핵심:** "DB 커밋이 됐다 = 이벤트는 언젠가 반드시 발행된다"

---

### Step 6 — Spring 도메인 이벤트 + 전략 후처리

```java
// Spring 내부 이벤트 (동기, 같은 JVM 내부)
eventPublisher.publishEvent(new OrderCreatedEvent(this, savedOrder));

// 전략별 후처리 (선택적 재정의)
strategy.postProcess(savedOrder.getId());
```

**Kafka vs Spring 이벤트 비교:**

| | Kafka (Outbox) | Spring ApplicationEvent |
|---|---|---|
| 범위 | 서비스 간 (MSA) | 같은 JVM 내 |
| 보장 | 적어도 1회 (at-least-once) | 트랜잭션 내 동기 실행 |
| 실패 처리 | Outbox Retry | 예외 전파 |
| 사용 예 | trading-engine에 주문 전달 | 캐시 무효화, 로그 등 |

---

## 4. updateOrderStatus() — 상태 변경 + 취소 시 증거금 해제

```java
@CacheEvict(value = "orders", key = "#id")
public OrderResponse updateOrderStatus(Long id, OrderStatus newStatus) {
    Order order = orderQueryPort.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));

    OrderStatus previousStatus = order.getStatus();
    order.updateStatus(newStatus);
    Order updated = orderCommandPort.save(order);

    // 취소 시 BUY 주문의 증거금 해제
    if (newStatus == OrderStatus.CANCELLED && "BUY".equalsIgnoreCase(order.getSide())) {
        BigDecimal orderAmount = order.getTotalPrice()
                .multiply(BigDecimal.valueOf(order.getQuantity()));
        accountServiceClient.unfreezeBalance(order.getCustomerName(), orderAmount);
    }

    // Outbox 이벤트 + Spring 이벤트 발행
    outboxService.save("Order", id, "ORDER_STATUS_CHANGED", ...);
    eventPublisher.publishEvent(new OrderStatusChangedEvent(...));
}
```

**`@CacheEvict` 역할:**
- `OrderQueryService`에서 주문을 캐시해두면 상태 변경 후에도 캐시가 남아 있을 수 있음
- `@CacheEvict(value = "orders", key = "#id")` → 해당 주문 캐시 즉시 무효화
- 쓰기 후 읽기 = 항상 최신 데이터 보장

---

## 5. deleteOrder() — 단순 삭제

```java
@CacheEvict(value = "orders", key = "#id")
public void deleteOrder(Long id) {
    orderQueryPort.findById(id)
            .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
    orderCommandPort.deleteById(id);
}
```

- 삭제 전 존재 여부 확인 → 없으면 400 에러 (404가 더 적절하나 현재 구현 기준 기록)
- 삭제 후 자동으로 캐시 무효화

---

## 6. Outbox 전체 구조 — 클래스 다이어그램

```
OrderCommandService
        │ outboxService.save(...)
        ▼
OutboxService
        │ save()
        ▼
OutboxEvent (JPA Entity)
  - aggregateType: "Order"
  - aggregateId: 1L
  - eventType: "ORDER_CREATED"
  - payload: "{...JSON...}"
  - topic: "order-events"
  - status: PENDING
  - retryCount: 0

[5초마다 스케줄러]
OutboxEventPublisher.publishPendingEvents()
        │
        ├─ KafkaTemplate.send(topic, key, payload).get()  ← 동기 대기
        │         성공 → event.markPublished()
        │         실패 → event.markFailed(e.getMessage())
        │                retryCount >= maxRetry(5) → DEAD_LETTER
        ▼
Kafka Topic: "order-events"
        ▼
trading-engine/OrderKafkaConsumer
```

---

## 7. 관련 파일 구조

```
order-service/
  domain/
    order/
      service/
        command/OrderCommandService.java    ← 이 파일
        query/OrderQueryService.java        ← 읽기 전용
      port/
        OrderCommandPort.java               ← 저장/삭제 인터페이스
        OrderQueryPort.java                 ← 조회 인터페이스
      strategy/
        OrderStrategy.java                  ← 전략 인터페이스
        OrderStrategyFactory.java           ← 팩토리
        LimitOrderStrategy.java
        MarketOrderStrategy.java
        StopLossOrderStrategy.java          ← 오늘 추가
        StopLimitOrderStrategy.java         ← 오늘 추가
      validator/
        OrderValidator.java                 ← 함수형 인터페이스 + andThen 체인
    outbox/
      entity/OutboxEvent.java
      service/OutboxService.java
      scheduler/OutboxEventPublisher.java   ← 5초마다 Kafka 발행
  infrastructure/
    client/AccountServiceClient.java        ← 오늘 추가 (증거금 동결/해제)
```

---

## 8. 실무에서 알아두면 좋은 포인트

### Q. `@Transactional`이 클래스에 붙어있는데 메서드마다 트랜잭션이 생기나?

**A.** 그렇다. 클래스에 `@Transactional`을 붙이면 **모든 public 메서드**에 트랜잭션이 적용된다.
개별 메서드에 `@Transactional(readOnly = true)` 등을 붙여 재정의 가능.

---

### Q. `orderCommandPort.save()` 와 `outboxService.save()` 는 같은 트랜잭션인가?

**A.** 그렇다. `createOrder()` 메서드 전체가 하나의 트랜잭션으로 묶여 있으므로:
- `orders` 테이블 INSERT
- `outbox_events` 테이블 INSERT
→ **한 트랜잭션 안에서 처리** → 하나라도 실패하면 둘 다 롤백

---

### Q. `AccountServiceClient.freezeBalance()`가 실패하면 트랜잭션이 롤백되나?

**A.** `freezeBalance()`는 **네트워크 호출이 먼저** 발생 → DB 저장은 그 이후.
freeze 실패 → `IllegalStateException` → 메서드 중단 → DB 저장이 아직 안 됨 → 자동으로 일관성 유지.

하지만 반대로: **DB 저장 후** account-service가 다운되면 증거금 해제 문제 발생 가능 → saga 패턴이나 보상 트랜잭션이 완전한 해결책.

---

### Q. `@CacheEvict`와 `@Transactional`이 같이 있으면 캐시는 언제 지워지나?

**A.** Spring 기본 동작: **트랜잭션이 커밋된 후** 캐시 무효화 실행.
→ 트랜잭션 롤백 시 캐시는 지워지지 않음 (안전)

---

## 9. 핵심 정리 — 이 클래스가 지킨 원칙

| 원칙 | 내용 |
|------|------|
| **SRP** | 주문 쓰기 작업만. 읽기는 QueryService에 위임 |
| **OCP** | 새 주문 타입 = Strategy 추가. createOrder() 수정 없음 |
| **DIP** | `OrderCommandPort`, `OrderStrategy` 인터페이스에만 의존. 구현체 모름 |
| **Outbox** | DB 저장 + 이벤트 저장 = 단일 트랜잭션. 메시지 소실 없음 |
| **CQRS** | Command / Query 클래스 완전 분리 |
