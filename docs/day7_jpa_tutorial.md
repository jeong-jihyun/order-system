# Day 7 학습 노트 — Week 1 최종 퀴즈 + JPA 실전 튜토리얼

> 날짜: 2026-04-09 | 주제: JPA 10문항 퀴즈 + 프로젝트 코드 기반 JPA 가이드

---

## 1교시 — Week 1 최종 퀴즈 결과

| # | 질문 | 결과 | 핵심 보완 |
|---|------|------|----------|
| Q1 | `@Entity` vs `@Table` | 보완 | `@Entity` = 클래스↔테이블 매핑 선언. `@Table` 없으면 클래스명이 테이블명 |
| Q2 | `IDENTITY` 전략 | ✅ | DB `AUTO_INCREMENT`. INSERT 후 ID 확인 → 배치 INSERT 불가 |
| Q3 | `PROTECTED` 이유 | ✅ | JPA 내부 요구 충족 + 외부 `new Order()` 차단 → `@Builder`와 세트 |
| Q4 | `STRING` vs `ORDINAL` | ✅ | `ORDINAL` = 중간 추가 시 기존 데이터 의미 바뀜 → 항상 `STRING` |
| Q5 | `LAZY` vs `EAGER` | 학습 | `EAGER` = N+1 문제. 연관 100개면 SQL 101번 |
| Q6 | JpaRepository 메서드 | ✅ | `findById`, `findAll`, `save`, `delete`, `count`, `existsById` |
| Q7 | `findByStatus` SQL | ✅ | 메서드명 파싱 → `WHERE status = ?` 자동 생성 (Derived Query) |
| Q8 | `PESSIMISTIC_WRITE` | ✅ | `SELECT FOR UPDATE` — 동시 출금 방지 |
| Q9 | 타임스탬프 차이 | ✅ | `@CreationTimestamp` = INSERT 1회, `@UpdateTimestamp` = 변경마다 갱신 |
| Q10 | `@Transactional` 없을 때 | 보완 | 단독 메서드는 내장 트랜잭션으로 안전. 여러 Repository 묶을 때 Service에 필수 |

---

## 2교시 — 프로젝트 코드로 배우는 JPA 실전 튜토리얼

---

### 1. @Entity + @Table — 클래스와 테이블 연결

```java
@Entity                    // ① 이 클래스가 DB 테이블과 매핑됨을 선언
@Table(name = "orders")    // ② 테이블 이름 명시 (없으면 클래스명 "Order" 사용)
public class Order { ... }
```

**실제 생성되는 DDL:**
```sql
CREATE TABLE orders (
    id          BIGINT AUTO_INCREMENT PRIMARY KEY,
    customer_name VARCHAR(50) NOT NULL,
    status      VARCHAR(20) NOT NULL,
    ...
);
```

> `@Entity`가 없으면 `@Table`이 있어도 아무 의미 없음 — `@Entity`가 전제 조건

---

### 2. @Id + @GeneratedValue — 기본키 전략

```java
// 프로젝트 전체 공통 패턴
@Id
@GeneratedValue(strategy = GenerationType.IDENTITY)
private Long id;
```

**4가지 전략 비교:**

| 전략 | 방식 | 추천 DB |
|------|------|--------|
| `IDENTITY` | DB `AUTO_INCREMENT` | MySQL ✅ (현재 프로젝트) |
| `SEQUENCE` | DB 시퀀스 객체 | Oracle, PostgreSQL |
| `TABLE` | 키 테이블 별도 관리 | 모든 DB (성능 나쁨) |
| `AUTO` | DB에 따라 자동 선택 | 개발 초기에만 |

**`IDENTITY`의 특징:**
- INSERT 실행 후 DB가 채워준 ID를 JPA가 읽어옴
- 배치 INSERT(여러 건 한번에) 최적화 불가 — 건별로 INSERT 후 ID 확인 필요

---

### 3. @Column — 컬럼 세부 설정

```java
// Order 엔티티에서 사용된 패턴들
@Column(nullable = false, length = 50)
private String customerName;               // NOT NULL, VARCHAR(50)

@Column(nullable = false, precision = 12, scale = 2)
private BigDecimal totalPrice;             // DECIMAL(12, 2)

@Column(precision = 12, scale = 2)        // nullable = true (생략 시 기본)
private BigDecimal stopPrice;             // STOP 주문에만 값 존재

@Column(updatable = false)
private LocalDateTime createdAt;          // INSERT 후 변경 불가
```

**`precision` vs `scale`:**
```
precision = 12, scale = 2
→ 전체 12자리, 소수점 이하 2자리
→ 최대값: 9,999,999,999.99
```

---

### 4. @Enumerated — Enum 저장 방식

```java
// 프로젝트 전체에서 항상 STRING 사용
@Enumerated(EnumType.STRING)
@Column(nullable = false, length = 20)
private OrderStatus status;    // DB에 "PENDING", "FILLED" 문자열 저장
```

**ORDINAL을 쓰면 안 되는 이유:**
```java
// 위험한 상황
public enum OrderStatus {
    PENDING,    // ORDINAL = 0
    FILLED,     // ORDINAL = 1  ← DB에 1로 저장
    CANCELLED   // ORDINAL = 2
}

// 나중에 PROCESSING 추가
public enum OrderStatus {
    PENDING,     // 0
    PROCESSING,  // 1  ← 새로 추가
    FILLED,      // 2  ← 기존 1이 2로 밀림 💥 데이터 오염
    CANCELLED    // 3
}
```

> **실무 규칙: `@Enumerated`는 항상 `EnumType.STRING`**

---

### 5. @ManyToOne + @JoinColumn — 연관관계

```java
// Account 엔티티
@ManyToOne(fetch = FetchType.LAZY)      // 지연 로딩
@JoinColumn(name = "user_id", nullable = false)  // FK 컬럼명
private User user;
```

**LAZY vs EAGER:**

```
EAGER (기본값, 위험):
account 조회 → 자동으로 user도 즉시 조회
→ account 100개 조회 시 SQL 101번 (N+1 문제) 💥

LAZY (권장):
account 조회 → user는 프록시 객체로 대체
→ account.getUser().getUsername() 호출 시 그때 user 조회
→ 필요할 때만 SQL 실행
```

**실무 규칙:**
```
@ManyToOne  → 항상 LAZY
@OneToOne   → 항상 LAZY
@OneToMany  → 기본값이 이미 LAZY
```

**N+1 해결 — JOIN FETCH:**
```java
@Query("SELECT a FROM Account a JOIN FETCH a.user WHERE a.id = :id")
Optional<Account> findWithUser(@Param("id") Long id);
// SQL 1번으로 account + user 동시 조회
```

---

### 6. @NoArgsConstructor(PROTECTED) + @Builder 패턴

```java
@NoArgsConstructor(access = AccessLevel.PROTECTED)   // JPA 요구사항 + 외부 차단
@AllArgsConstructor                                   // @Builder가 내부적으로 사용
@Builder
public class Order { ... }
```

**왜 이 조합인가:**
```java
// 외부에서 new Order() 불가 (PROTECTED)
Order order = new Order(); // 컴파일 에러 ✅

// 유일한 생성 경로 = Builder
Order order = Order.builder()
    .customerName("홍길동")
    .productName("AAPL")
    .quantity(10)
    .totalPrice(new BigDecimal("1500000"))
    .status(OrderStatus.PENDING)
    .build();
```

> 필수 필드가 빠지면 빌드 단계에서 발견 가능 — 불완전한 객체 생성 방지

---

### 7. JpaRepository — 자동 제공 메서드

```java
public interface OrderRepository extends JpaRepository<Order, Long> {
    // 아래는 직접 선언한 메서드
    List<Order> findByStatus(OrderStatus status);
    List<Order> findByCustomerName(String customerName);
}
// JpaRepository가 자동으로 제공하는 메서드:
// findById(Long id)       → Optional<Order>
// findAll()               → List<Order>
// findAll(Pageable)       → Page<Order>
// save(Order)             → Order  (insert or update)
// saveAll(List<Order>)    → List<Order>
// deleteById(Long id)     → void
// delete(Order)           → void
// count()                 → long
// existsById(Long id)     → boolean
```

**`save()` = INSERT or UPDATE 자동 판단:**
```java
Order order = Order.builder()...build(); // id = null
orderRepository.save(order);  // → INSERT, DB가 id 채워줌

order.updateStatus(OrderStatus.FILLED);
orderRepository.save(order);  // id 있음 → UPDATE
```

---

### 8. Derived Query (쿼리 메서드) — 메서드명 → SQL 자동 생성

```java
// 선언만 하면 JPA가 SQL 자동 생성
List<Order> findByStatus(OrderStatus status);
// → SELECT * FROM orders WHERE status = ?

List<Order> findByCustomerName(String name);
// → SELECT * FROM orders WHERE customer_name = ?
```

**메서드명 조합 규칙:**

| 키워드 | SQL |
|--------|-----|
| `findBy필드` | `WHERE 필드 = ?` |
| `findBy필드And필드` | `WHERE 필드 = ? AND 필드 = ?` |
| `findBy필드Or필드` | `WHERE 필드 = ? OR 필드 = ?` |
| `findBy필드GreaterThan` | `WHERE 필드 > ?` |
| `findBy필드Containing` | `WHERE 필드 LIKE '%?%'` |
| `findBy필드Between` | `WHERE 필드 BETWEEN ? AND ?` |
| `findBy필드OrderBy필드Desc` | `WHERE ... ORDER BY 필드 DESC` |
| `countBy필드` | `SELECT COUNT(*) WHERE 필드 = ?` |
| `existsBy필드` | `SELECT EXISTS(...)` |

---

### 9. @Lock — 비관적 잠금 (동시성 제어)

```java
// AccountRepository — 잔고 변경 시 사용
@Lock(LockModeType.PESSIMISTIC_WRITE)
@Query("SELECT a FROM Account a WHERE a.id = :id")
Optional<Account> findByIdForUpdate(Long id);
```

**왜 필요한가 (동시 출금 시나리오):**

```
잔고: 10,000원

스레드A (출금 8,000원)       │  스레드B (출금 8,000원)
잔고 읽기 = 10,000           │  잔고 읽기 = 10,000
8,000 < 10,000 → 가능 ✅     │  8,000 < 10,000 → 가능 ✅  💥
잔고 = 2,000 저장            │  잔고 = 2,000 저장
```

**`PESSIMISTIC_WRITE` 적용 후:**
```sql
-- 스레드A
SELECT * FROM accounts WHERE id = 1 FOR UPDATE  ← 행 락
-- 스레드B: 락 걸려있음 → 대기
-- 스레드A 커밋 후 락 해제
-- 스레드B: 잔고 읽기 = 2,000 → 출금 불가 ✅
```

**비관적 락 vs 낙관적 락:**

| | 비관적 락 | 낙관적 락 |
|--|---------|---------|
| 방식 | `FOR UPDATE` (미리 잠금) | `@Version` 컬럼 (충돌 시 예외) |
| 사용처 | 잔고, 재고 — 충돌 잦음 | 게시글 수정 — 충돌 드묾 |
| 성능 | 대기 발생 가능 | 빠름 |

---

### 10. @Transactional — 여러 작업의 원자성 보장

```java
// JpaRepository 기본 메서드는 이미 내장 트랜잭션
@Transactional(readOnly = true)
Optional<Order> findById(Long id);   // 내장 ✅

@Transactional
Order save(Order order);             // 내장 ✅
```

**Service에서 반드시 필요한 경우:**
```java
// @Transactional 없으면
public void createOrderAndFreezeBalance(OrderRequest request) {
    orderRepository.save(order);              // 트랜잭션1 커밋
    accountRepository.freeze(amount);         // 트랜잭션2 — 여기서 예외 💥
    // order는 저장됐는데 잔고는 안 동결된 상태 → 데이터 불일치
}

// @Transactional 있으면
@Transactional
public void createOrderAndFreezeBalance(OrderRequest request) {
    orderRepository.save(order);              // 같은 트랜잭션
    accountRepository.freeze(amount);         // 같은 트랜잭션
    // 예외 발생 시 둘 다 롤백 ✅
}
```

---

### 11. @CreationTimestamp + @UpdateTimestamp

```java
@CreationTimestamp
@Column(updatable = false)           // DB 레벨에서도 수정 차단
private LocalDateTime createdAt;     // INSERT 시 1회만 설정

@UpdateTimestamp
private LocalDateTime updatedAt;     // save() 호출마다 현재 시각으로 갱신
```

---

### 12. Hexagonal Architecture — Repository Adapter 패턴

프로젝트가 사용하는 구조:

```
OrderCommandService
        │ depends on
        ▼
OrderCommandPort (interface)    ← 서비스는 이 인터페이스만 알고 있음
        ▲ implements
OrderRepositoryAdapter          ← JPA 구현체가 여기에만 위치
        │ uses
OrderRepository (JpaRepository)
```

**왜 이 구조인가:**
```java
// 서비스는 JPA를 직접 모름
private final OrderCommandPort orderCommandPort; // 인터페이스만 의존

// 테스트 시 인메모리 구현으로 교체 가능
OrderCommandPort fake = new InMemoryOrderRepository();
```

> DIP(의존 역전 원칙) — 고수준 모듈(Service)이 저수준 모듈(JPA)을 직접 의존하지 않음

---

## 핵심 정리표

| JPA 개념 | 프로젝트 사용 위치 | 한 줄 요약 |
|---------|-----------------|----------|
| `@Entity` | 모든 엔티티 | 클래스↔테이블 매핑 선언 |
| `IDENTITY` | 모든 `@Id` | DB AUTO_INCREMENT에 위임 |
| `AccessLevel.PROTECTED` | 모든 엔티티 | JPA 요구 + 외부 생성 차단 |
| `EnumType.STRING` | OrderStatus, UserRole 등 | Enum 이름을 문자열로 저장 — 순서 변경 안전 |
| `FetchType.LAZY` | `Account.user`, `Holding.user` | N+1 방지 — 필요할 때만 조회 |
| `@Lock(PESSIMISTIC_WRITE)` | `AccountRepository`, `HoldingRepository` | 동시 잔고/보유 수량 변경 방지 |
| `@CreationTimestamp` | 모든 엔티티 | INSERT 시 자동 기록, 이후 변경 불가 |
| `@Transactional` | 모든 Service | 여러 Repository 묶어서 원자성 보장 |
| Derived Query | `findByStatus`, `findByCustomerName` | 메서드명 → SQL 자동 생성 |
| Repository Adapter | `OrderRepositoryAdapter` | DIP — 서비스와 JPA 구현 분리 |
