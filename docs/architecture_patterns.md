# 아키텍처 패턴 & SOLID 원칙 기록

> 날짜: 2026-04-08 | 오늘 적용/추가된 구조를 중심으로 정리

---

## 1. 오늘 추가된 구조 전체 요약

```
order-service
  └── domain/order/strategy/
        ├── OrderStrategy.java          ← 인터페이스 (계약)
        ├── LimitOrderStrategy.java     ← 지정가
        ├── MarketOrderStrategy.java    ← 시장가
        ├── StopLossOrderStrategy.java  ← 손절 (신규)
        ├── StopLimitOrderStrategy.java ← 스탑-리밋 (신규)
        └── OrderStrategyFactory.java   ← 팩토리 (전략 자동 수집)
  └── infrastructure/client/
        └── AccountServiceClient.java   ← 서비스 간 REST 클라이언트 (신규)

trading-engine
  └── domain/matching/service/
        └── StopOrderManager.java       ← STOP 주문 대기 + 트리거 관리 (신규)

account-service
  └── domain/holding/
        ├── entity/Holding.java         ← 보유 종목 엔티티 (신규)
        ├── service/HoldingService.java ← 매수/매도 시 보유 수량·평균단가 계산 (신규)
        └── repository/HoldingRepository.java
  └── infrastructure/kafka/
        └── SettlementEventConsumer.java ← 정산 이벤트 수신 → 잔고+보유 반영 (신규)
```

---

## 2. Strategy 패턴 (전략 패턴)

### 언제 쓰나?
> "같은 동작(주문 처리)을 하되, **알고리즘(검증·전처리)이 타입마다 다를 때**"

### 구조

```
               «interface»
             OrderStrategy
          ┌────────────────┐
          │ getSupportedType() │
          │ validate()         │
          │ preProcess()       │  ← default (선택적 재정의)
          │ postProcess()      │  ← default (선택적 재정의)
          └────────────────┘
                 ▲
    ┌────────────┼────────────┬────────────┐
    │            │            │            │
LimitOrder  MarketOrder  StopLoss   StopLimit
Strategy    Strategy     Strategy   Strategy
```

### 코드 핵심

```java
// 인터페이스
public interface OrderStrategy {
    OrderType getSupportedType();
    void validate(OrderRequest request);

    default void preProcess(OrderRequest request) {}  // 선택 재정의
    default void postProcess(Long orderId) {}          // 선택 재정의
}

// 각 전략은 @Component만 붙이면 자동 등록
@Component
public class StopLossOrderStrategy implements OrderStrategy {
    @Override
    public OrderType getSupportedType() { return OrderType.STOP_LOSS; }

    @Override
    public void validate(OrderRequest request) {
        if (request.getStopPrice() == null)
            throw new IllegalArgumentException("손절 주문은 stopPrice 필수");
    }
}
```

### 실무 포인트
- 새로운 주문 타입 추가 = **클래스 파일 하나만 추가** → 기존 코드 수정 없음
- `if/else` 또는 `switch`로 타입마다 분기하는 "신호" → 전략 패턴 도입을 검토

---

## 3. Factory 패턴 (팩토리 패턴) + Spring DI 결합

### 구조

```java
@Component
public class OrderStrategyFactory {

    private final Map<OrderType, OrderStrategy> strategies;

    // Spring이 OrderStrategy 구현체 전부를 List로 주입
    public OrderStrategyFactory(List<OrderStrategy> strategyList) {
        this.strategies = strategyList.stream()
                .collect(Collectors.toMap(OrderStrategy::getSupportedType, s -> s));
    }

    public OrderStrategy getStrategy(OrderType type) {
        OrderStrategy strategy = strategies.get(type);
        if (strategy == null)
            throw new IllegalArgumentException("지원하지 않는 주문 타입: " + type);
        return strategy;
    }
}
```

### 왜 Map으로 미리 만들어 두나?
| 방법 | 호출할 때마다 | 성능 |
|------|-------------|------|
| `if/else` 분기 | O(n) | 타입 증가 시 느려짐 |
| `Map<타입, 전략>` | **O(1)** | 타입이 늘어나도 동일 |

### 실무 포인트
- `List<인터페이스>` 주입 → Spring이 해당 인터페이스의 **모든 구현체를 자동으로** 주입
- 애플리케이션 시작 시 1회만 Map 구성 → 런타임 비용 없음

---

## 4. CQRS 패턴 (Command Query Responsibility Segregation)

### 구조

```
OrderCommandService   ← 쓰기 전용 (create, update, cancel)
        │
        ├─ OrderCommandPort (save, delete)
        └─ OrderStrategyFactory + AccountServiceClient

OrderQueryService     ← 읽기 전용 (findById, findAll, stream 분석)
        │
        └─ OrderQueryPort (findById, findAll)
```

### 왜 나누나?
- **쓰기**는 트랜잭션, 이벤트 발행, 증거금 동결 등 부수효과가 많음
- **읽기**는 캐싱, 페이징, 집계에 최적화 가능
- 한 클래스에 섞으면 변경 이유가 2가지 → SRP 위반

---

## 5. Outbox 패턴 (이중 쓰기 문제 해결)

### 문제 상황
```
주문 DB 저장 → Kafka 발행 (네트워크 실패 가능)
```
DB는 성공했는데 Kafka 발행이 실패하면 → **데이터 불일치**

### Outbox 해결

```
┌─────────────────────────────┐  단일 트랜잭션
│  orders 테이블에 주문 Insert │
│  outbox 테이블에 이벤트 Insert│
└─────────────────────────────┘
         ↓ 별도 스케줄러 (신뢰성 있는 발행)
      Kafka topic 발행 (outbox 레코드 처리 후 삭제)
```

### 코드 핵심

```java
// OrderCommandService.createOrder()
// 주문 저장 + outbox 저장 = 같은 @Transactional
outboxService.save("Order", savedOrder.getId(),
        "ORDER_CREATED", KafkaConfig.ORDER_TOPIC, payload);
```

### 실무 포인트
- DB + 이벤트 시스템이 함께 쓰이는 **모든 마이크로서비스**에서 권장
- 이것 없이 Kafka를 직접 발행하면 "주문은 됐는데 처리가 안 되는" 버그 발생 가능

---

## 6. @Lazy로 순환 의존성 해결

### 문제

```
StopOrderManager → ExecutionService (processOrder 호출)
ExecutionService → StopOrderManager (checkTriggers 호출)
→ 스프링 순환 참조 오류 BeanCurrentlyInCreationException
```

### 해결

```java
@Autowired
public StopOrderManager(@Lazy ExecutionService executionService) {
    this.executionService = executionService;
}
```

### @Lazy 동작 원리

```
일반: 앱 시작 → 두 빈 동시 생성 → 서로를 참조 → 실패
@Lazy: 앱 시작 → StopOrderManager 생성 (프록시로 대체)
             → 실제 ExecutionService는 처음 호출 시 생성
```

### 실무 포인트
- `@Lazy`는 임시방편이 될 수 있으므로 **구조를 먼저 검토** (이벤트, 인터페이스 분리 등)
- 불가피하게 양방향 의존성이 생기는 경우 (ex. 매칭엔진 ↔ 스탑주문 관리) → `@Lazy` 적합

---

## 7. Rich Domain Model (풍부한 도메인 모델)

### 안티패턴: Anemic Domain Model (빈약한 도메인 모델)

```java
// 나쁜 예 — 엔티티는 getter/setter만, 로직은 Service에 다 몰림
class Holding {
    private BigDecimal quantity;
    private BigDecimal averagePrice;
    // getter/setter만 존재
}

// HoldingService에서 모든 계산 직접
holding.setQuantity(holding.getQuantity().add(buyQuantity));
holding.setAveragePrice(...복잡한 계산...);
```

### 실제 구현: Rich Domain Model

```java
// Holding 엔티티 안에 비즈니스 로직이 들어있음
public void buy(BigDecimal buyQuantity, BigDecimal buyPrice) {
    BigDecimal newInvestment = buyPrice.multiply(buyQuantity);
    this.totalInvestment = this.totalInvestment.add(newInvestment);
    this.quantity = this.quantity.add(buyQuantity);
    this.averagePrice = this.totalInvestment
            .divide(this.quantity, 8, RoundingMode.HALF_UP);
}

public void sell(BigDecimal sellQuantity) {
    if (this.quantity.compareTo(sellQuantity) < 0)
        throw new IllegalStateException("보유 수량 부족");
    // ... 수량, 평균단가 업데이트
}
```

### 왜 좋은가?
- "매수/매도" 로직이 **Holding 곁에 위치** → 응집도(Cohesion) 향상
- Service에서 호출 시 `holding.buy(qty, price)` 한 줄로 끝
- 단위 테스트: Holding만 테스트하면 됨 (Service 없이)

---

## 8. Event-Driven Architecture (이벤트 기반 아키텍처)

### 정산 흐름 전체

```
trading-engine (체결 발생)
        │ Kafka: execution-events
        ▼
settlement-service (정산 계산 — 수수료, 세금 반영)
        │ Kafka: settlement-events
        ▼
account-service/SettlementEventConsumer
        ├─ AccountService.deposit/withdraw (잔고 반영)
        └─ HoldingService.updateHolding (보유 종목 반영)
```

### 장점
- 서비스 간 **직접 REST 호출 없음** → 결합도 낮음
- trading-engine은 settlement-service가 어디 있는지 모름
- account-service는 trading-engine을 모름

### 단점 / 주의사항
- 이벤트 유실 가능 → **Outbox 패턴** 병행 필요
- 처리 순서 보장 어려움 → Kafka 파티션 전략 신경 써야 함
- 디버깅 어려움 → 로그에 orderId/messageId 추적 필수

---

## 9. 서비스 간 통신 — AccountServiceClient

### 구조 (Facade 패턴 + 단순 HTTP Client)

```java
@Component
public class AccountServiceClient {

    public boolean freezeBalance(String username, BigDecimal amount) { ... }
    public void unfreezeBalance(String username, BigDecimal amount) { ... }
}
```

### 실무 포인트
- `@Value("${order.account-service-url:...}")` → 기본값 포함 외부 주입 → 테스트 시 Mock URL 교체 가능
- try/catch로 실패 시 `false` 반환 → 잔고 부족 vs 서버 오류를 분리 처리
- 실무 프로젝트에서는 `OpenFeign` 또는 `WebClient` 사용 권장

#### OpenFeign vs RestTemplate 비교

| | `RestTemplate` | `OpenFeign` |
|---|---|---|
| 코드량 | 많음 (URL, HttpEntity 직접) | 적음 (인터페이스 선언만) |
| 타임아웃 설정 | 직접 `RestTemplateBuilder` | yml로 간단 설정 |
| 서킷브레이커 | 직접 구현 | Resilience4j 연동 쉬움 |
| 학습 난도 | 낮음 | 중간 |

---

## 10. Thread-safe 자료구조 — StopOrderManager

```java
private final ConcurrentHashMap<String, CopyOnWriteArrayList<StopOrderEntry>> pendingStops
        = new ConcurrentHashMap<>();
```

| 자료구조 | 특징 | 사용 이유 |
|---------|------|----------|
| `ConcurrentHashMap` | 세그먼트 락 — 동시 쓰기 안전 | 여러 종목 동시 처리 |
| `CopyOnWriteArrayList` | 쓰기 시 배열 복사 — 읽기 중 순회 안전 | 체결 루프 중 STOP 삭제 충돌 방지 |

### 주의
- `CopyOnWriteArrayList`: 쓰기(추가/삭제)가 잦으면 성능 저하 → 쓰기가 드문 상황에 적합
- STOP 주문은 등록(쓰기)은 드물고 순회(읽기)는 체결마다 발생 → 적합한 선택

---

## 11. SOLID 원칙 체크리스트

### S — 단일 책임 원칙 (Single Responsibility Principle)

| 클래스 | 책임 하나? | 비고 |
|-------|---------|------|
| `OrderCommandService` | ✅ | 주문 생성/수정/취소만 |
| `OrderQueryService` | ✅ | 주문 조회/집계만 |
| `HoldingService` | ✅ | 보유 종목 CRUD만 |
| `StopOrderManager` | ✅ | STOP 주문 대기 관리만 |
| `SettlementEventConsumer` | ⚠️ | 잔고 반영 + 보유 반영 2가지 → 추후 분리 검토 |

### O — 개방-폐쇄 원칙 (Open-Closed Principle)

```
OrderStrategy ← 확장에 열려있음 (새 전략 클래스 추가)
               폐쇄에 닫혀있음 (OrderCommandService 수정 없음)

새 주문 타입 추가 흐름:
1. XXXOrderStrategy.java 파일 추가 (@Component 선언)
2. OrderStrategyFactory → 자동 Map에 등록
3. 기존 코드 변경 없음
```

### L — 리스코프 치환 원칙 (Liskov Substitution Principle)

```java
// OrderCommandService는 OrderStrategy(인터페이스)만 알고 있음
OrderStrategy strategy = strategyFactory.getStrategy(orderType);
strategy.validate(request);   // 어떤 구현체가 와도 동일하게 동작
strategy.preProcess(request);
```
→ `MarketOrderStrategy`, `StopLossOrderStrategy` 어떤 것이 와도 교체 가능

### I — 인터페이스 분리 원칙 (Interface Segregation Principle)

```java
public interface OrderStrategy {
    OrderType getSupportedType(); // 최소한의 계약
    void validate(OrderRequest request);
    default void preProcess(OrderRequest request) {}  // 선택 재정의
    default void postProcess(Long orderId) {}          // 선택 재정의
}
```
→ 구현체는 자신에게 필요한 메서드만 재정의. 불필요한 메서드 강제 없음

### D — 의존 역전 원칙 (Dependency Inversion Principle)

```
나쁜 예:  OrderCommandService → StopLossOrderStrategy (구체 클래스)
좋은 예:  OrderCommandService → OrderStrategy (인터페이스)
                                      ↑
                              StopLossOrderStrategy
                              StopLimitOrderStrategy
                              LimitOrderStrategy
```

---

## 12. 오늘 새로 생긴 흐름 — 매수 주문 전체 사이클

```
클라이언트
  → POST /api/v1/orders
  → OrderCommandService.createOrder()
        ├─ OrderValidator.validate()          // 기본 검증
        ├─ OrderStrategyFactory.getStrategy() // 전략 선택 (Strategy 패턴)
        ├─ strategy.validate()               // 타입별 검증
        ├─ AccountServiceClient.freeze()     // 증거금 동결 (서비스 간 호출)
        ├─ orders 테이블 Insert
        └─ outbox 테이블 Insert              // Outbox 패턴 (원자성)

  → OutboxEventPublisher (스케줄러)
        └─ Kafka: order-events 발행

  → trading-engine/OrderKafkaConsumer
        ├─ STOP 주문 → StopOrderManager.register()   // 대기
        └─ 일반 주문 → MatchingEngine 처리            // 즉시 체결 시도

  → 체결 발생 시 StopOrderManager.checkTriggers()
        └─ 조건 충족 → ExecutionService.processOrder()

  → Kafka: settlement-events 발행

  → account-service/SettlementEventConsumer
        ├─ AccountService: 잔고 반영 (입금/출금)
        └─ HoldingService.updateHolding()    // 보유 종목 업데이트 (Rich Domain Model)
```

---

## 13. 기억할 실무 용어

| 용어 | 설명 |
|------|------|
| **이동평균 단가** | 매수마다 `(총투자금 / 총수량)` 으로 재계산 |
| **증거금 동결** | 주문 접수 시 잔고에서 '묶어두기' (취소 시 해제) |
| **STOP_LOSS** | 가격이 stopPrice 아래로 내려가면 즉시 시장가 매도 (손절) |
| **STOP_LIMIT** | STOP_LOSS와 동일하지만 지정가로 매도 (슬리피지 방지) |
| **Outbox Table** | 이벤트 발행을 DB 트랜잭션에 묶기 위한 중간 테이블 |
| **CQRS** | 읽기/쓰기 서비스 분리 — 독립 확장 가능 |
| **Rich Domain Model** | 엔티티에 비즈니스 로직 포함 (↔ Anemic = getter/setter만) |
