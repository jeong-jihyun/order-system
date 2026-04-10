# Day 8 학습 노트 — Redis @Cacheable / @CacheEvict

> 날짜: 2026-04-10 | 주제: Redis 캐싱 전략 — 처음부터 전체 흐름

---

## 1. 캐시가 왜 필요한가?

### 캐시 없는 상황
```
클라이언트 1000명 → 같은 주문 조회
    ↓ (매번)
DB 쿼리 1000번 실행 → DB 부하 증가, 응답 느려짐
```

### 캐시 있는 상황
```
클라이언트 1000명 → 같은 주문 조회
    ↓
Redis 확인
    ├─ 있으면 → 즉시 반환 (DB 안 씀) ✅  → 999번
    └─ 없으면 → DB 조회 → Redis 저장 → 반환 → 1번
```
→ DB 쿼리 1번으로 1000명 응답 가능

---

## 2. Redis란?

> **메모리 기반 Key-Value 저장소**

| 저장소 | 위치 | 속도 |
|--------|------|------|
| MySQL (DB) | 디스크 | 수십 ms |
| Redis | 메모리 | 1ms 이하 |

**Redis에 저장되는 구조:**
```
Key              Value
-----------      ------------------------------------------
"orders::1"  →  {"id":1, "customerName":"홍길동", "status":"PENDING", ...}
"orders::2"  →  {"id":2, "customerName":"이순신", "status":"FILLED", ...}
```

---

## 3. 3가지 핵심 어노테이션

| 어노테이션 | 역할 | 위치 |
|-----------|------|------|
| `@EnableCaching` | 캐시 기능 전원 ON | `@Configuration` 클래스 (1번만) |
| `@Cacheable` | 조회 시 캐시 저장/조회 | Service 읽기 메서드 |
| `@CacheEvict` | 수정/삭제 시 캐시 삭제 | Service 쓰기 메서드 |

> `@EnableCaching`이 없으면 `@Cacheable`과 `@CacheEvict`는 전부 무시됨

---

## 4. @EnableCaching — 캐시 전원 ON

```java
// order-service/config/RedisConfig.java
@EnableCaching      // ← 캐시 기능 활성화 스위치
@Configuration
public class RedisConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(10))  // 캐시 유효시간 10분 (TTL)
                .serializeKeysWith(...)             // 키를 String으로 직렬화
                .serializeValuesWith(...);          // 값을 JSON으로 직렬화

        return RedisCacheManager.builder(factory).cacheDefaults(config).build();
    }
}
```

**TTL(Time To Live)이 왜 필요한가?**
```
TTL 없으면:
    캐시가 Redis에 영구히 남음 → DB 값이 바뀌어도 캐시는 예전 데이터 유지
    @CacheEvict를 빠뜨린 메서드가 있으면 영원히 오래된 데이터 반환 💥

TTL = 10분이면:
    @CacheEvict가 없어도 10분 후에는 자동으로 캐시 삭제
    최악의 경우 10분짜리 지연만 발생
```

---

## 5. @Cacheable — 조회 시 동작

```java
// OrderQueryService.java
@Cacheable(value = "orders", key = "#id")
public OrderResponse getOrder(Long id) {
    return orderQueryPort.findById(id)
            .map(OrderResponse::from)
            .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다."));
}
```

**속성 설명:**
| 속성 | 값 | 의미 |
|------|-----|------|
| `value` | `"orders"` | 캐시 저장소 이름 → Redis 키 앞에 붙음 |
| `key` | `"#id"` | 캐시 키 (`#` = 파라미터 참조) |

**Redis 실제 키:**
```
orders::1   → id=1 주문
orders::2   → id=2 주문
orders::99  → id=99 주문
```

**동작 순서:**
```
1. getOrder(1) 호출
2. Redis "orders::1" 확인
3. [캐시 히트]  있으면 → 메서드 실행하지 않고 Redis 값 바로 반환
4. [캐시 미스]  없으면 → 메서드 실행 → DB 조회 → 결과를 Redis에 저장 → 반환
```

---

## 6. @CacheEvict — 수정/삭제 시 캐시 삭제

```java
// OrderCommandService.java
@CacheEvict(value = "orders", key = "#id")
public OrderResponse updateOrderStatus(Long id, OrderStatus newStatus) {
    // DB 업데이트...
}

@CacheEvict(value = "orders", key = "#id")
public void deleteOrder(Long id) {
    // DB 삭제...
}
```

**왜 삭제해야 하나?**
```
[상황]
DB:    orders id=1 → status = FILLED  (방금 변경)
Redis: "orders::1" → status = PENDING (예전 데이터 남아있음)

@CacheEvict 없으면:
    다음 조회 → Redis에서 PENDING 반환 💥 (DB는 FILLED인데)

@CacheEvict 있으면:
    업데이트 → Redis "orders::1" 삭제
    다음 조회 → Redis 없음 → DB에서 FILLED 조회 → 반환 ✅
```

---

## 7. 전체 흐름 한눈에 보기

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[첫 번째 조회] getOrder(1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Redis "orders::1" 확인 → 없음 (캐시 미스)
    ↓
DB 조회 → {id:1, status:PENDING}
    ↓
Redis "orders::1" 저장 (TTL 10분)
    ↓
클라이언트에 반환

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[두 번째 조회] getOrder(1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Redis "orders::1" 확인 → 있음 (캐시 히트) ✅
    ↓
DB 쿼리 없이 Redis 값 바로 반환

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[수정] updateOrderStatus(1, FILLED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DB 업데이트 → status = FILLED
    ↓
Redis "orders::1" 삭제 (@CacheEvict)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[수정 후 조회] getOrder(1)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Redis "orders::1" 확인 → 없음 (방금 삭제됨)
    ↓
DB 조회 → {id:1, status:FILLED}  ← 최신 데이터
    ↓
Redis "orders::1" 재저장
    ↓
클라이언트에 반환
```

---

## 8. CQRS와 캐시의 관계

```
OrderQueryService    ← @Cacheable (읽기)
OrderCommandService  ← @CacheEvict (쓰기)
```

**왜 분리했나?**
- 한 클래스 안에서 `this.getOrder()` 내부 호출 시 캐시 동작 안 함 (프록시 우회 문제)
- 두 클래스로 나누면 → `Controller`에서 각각 외부 호출 → 프록시 정상 동작

**프록시 구조:**
```
외부 호출: Controller → [Spring 프록시] → getOrder()
                              ↑
                         여기서 @Cacheable 처리

내부 호출: this.getOrder()  ← 프록시 우회 → @Cacheable 무시됨 💥
```

---

## 9. Cache-Aside 패턴

> 프로젝트에서 사용하는 캐싱 전략 이름

```
1. 애플리케이션이 Redis 먼저 확인
2. 있으면 → 반환 (Cache Hit)
3. 없으면 → DB 조회 → Redis 저장 → 반환 (Cache Miss)
4. 데이터 변경 시 → Redis 삭제 (Invalidation)
```

**다른 패턴과 비교:**

| 패턴 | 방식 | 특징 |
|------|------|------|
| **Cache-Aside** | 앱이 캐시 직접 관리 | 가장 일반적. 프로젝트 사용 ✅ |
| Write-Through | 쓰기 시 캐시+DB 동시 저장 | 캐시 항상 최신. 쓰기 느림 |
| Write-Behind | 캐시에 쓰고 나중에 DB 반영 | 빠름. 유실 위험 |
| Read-Through | 캐시가 DB 조회 담당 | 앱 코드 단순. 설정 복잡 |

---

## 10. 핵심 정리

| 개념 | 한 줄 요약 |
|------|----------|
| Redis | 메모리 Key-Value 저장소. DB보다 100배 빠름 |
| `@EnableCaching` | 캐시 기능 ON. 없으면 나머지 어노테이션 무시 |
| `@Cacheable(value, key)` | 캐시 히트 시 메서드 실행 건너뜀. 미스 시 DB 조회 후 저장 |
| `@CacheEvict(value, key)` | 수정/삭제 후 캐시 무효화. 같은 value+key로 맞춰야 함 |
| TTL | 캐시 유효시간. 설정 안 하면 오래된 데이터 영구 잔류 위험 |
| 프록시 함정 | 같은 클래스 내부 `this.` 호출 시 @Cacheable 무시됨 |
| Cache-Aside | 앱이 캐시 직접 관리하는 패턴. 가장 일반적 |
