# Day 9 학습 노트 — Redis TTL 설정 + Cache-Aside 패턴 실습

> 날짜: 2026-04-10 | 주제: 캐시별 TTL 다르게 설정 + Cache-Aside 수동 구현

---

## 1. 캐시별 TTL 다르게 설정하기

### 문제 — 현재는 모든 캐시가 똑같이 10분

```java
// 기존: 전체 캐시 기본값만 설정
return RedisCacheManager.builder(factory)
        .cacheDefaults(config)  // 모든 캐시 → 10분
        .build();
```

### 왜 캐시마다 TTL이 달라야 하나?

```
"orders" (주문 상태)
  → 주문 상태는 자주 바뀜 (PENDING → FILLED → SETTLED)
  → TTL 길면 오래된 상태가 캐시에 남음
  → 짧게: 5분

"products" (상품 정보)
  → 상품 이름/가격은 거의 안 바뀜
  → TTL 짧으면 매번 DB 조회 → 캐시 의미 없음
  → 길게: 30분
```

### 해결 — withCacheConfiguration으로 개별 설정

```java
// order-service/config/RedisConfig.java (수정 후)
return RedisCacheManager.builder(factory)
        .cacheDefaults(config)                                      // 기본값 (나머지 캐시 → 10분)
        .withCacheConfiguration("orders",                           // orders만 5분
                config.entryTtl(Duration.ofMinutes(5)))
        .withCacheConfiguration("products",                         // products만 30분
                config.entryTtl(Duration.ofMinutes(30)))
        .build();
```

**핵심:** `config.entryTtl(...)` 은 **기존 config를 복사한 새 객체** 반환 → 원본 `config`(10분) 유지됨

**결과:**
```
"orders::*"   → TTL 5분   (withCacheConfiguration 적용)
"products::*" → TTL 30분  (withCacheConfiguration 적용)
그 외 캐시    → TTL 10분  (cacheDefaults 적용)
```

---

## 2. Cache-Aside 패턴 4단계

> "앱이 캐시를 직접 관리한다"는 전략. 프로젝트에서 사용하는 방식.

```
1단계. 조회 요청 들어옴
           ↓
2단계. 캐시 먼저 확인
           ├─ 있으면 (Hit)  → 캐시에서 바로 반환 → 끝
           └─ 없으면 (Miss) → 3단계로
           ↓
3단계. DB에서 조회
           ↓
4단계. 조회 결과를 캐시에 저장 → 반환
```

**수정/삭제 발생 시 (Invalidation):**
```
DB 업데이트 → 해당 캐시 삭제
다음 조회 → Miss → DB 조회 (최신) → 캐시 재저장
```

---

## 3. Cache-Aside 수동 구현 (@Cacheable 없이)

```java
public OrderResponse getOrderManual(Long id) {
    String cacheKey = "orders::" + id;

    // 1단계 + 2단계: Redis 확인 → Hit이면 바로 반환
    String cached = redisTemplate.opsForValue().get(cacheKey);
    if (cached != null) {
        try {
            return objectMapper.readValue(cached, OrderResponse.class);
            //                  ↑                  ↑
            //          Redis JSON 문자열    변환할 목표 클래스
        } catch (JsonProcessingException e) {
            log.warn("[캐시 역직렬화 실패] key={}", cacheKey);
            // 실패 시 캐시 무시하고 DB 조회로 fall-through
        }
    }

    // 3단계: 캐시 Miss → DB 조회
    OrderResponse response = orderQueryPort.findById(id)
            .map(OrderResponse::from)
            .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다."));

    // 4단계: Redis에 저장 (TTL 5분)
    try {
        String json = objectMapper.writeValueAsString(response);
        //                         ↑
        //               Java 객체 → JSON 문자열
        redisTemplate.opsForValue().set(cacheKey, json, Duration.ofMinutes(5));
        //                              ↑      ↑          ↑
        //                             키     값       TTL 5분
    } catch (JsonProcessingException e) {
        log.warn("[캐시 저장 실패] key={}", cacheKey);
        // 실패 시 캐시 저장 생략, 조회는 정상 반환
    }

    return response;
}
```

---

## 4. 체크 예외(Checked Exception) 처리

`objectMapper`의 두 메서드는 **체크 예외**를 던짐 → 반드시 처리 필요

| 메서드 | 예외 | 방향 |
|--------|------|------|
| `readValue()` | `JsonProcessingException` | 역직렬화 실패 → 캐시 무시, DB 조회 |
| `writeValueAsString()` | `JsonProcessingException` | 직렬화 실패 → 캐시 저장 생략, 결과는 반환 |

**처리 방식 2가지:**
```java
// 1. try-catch (우리 선택 — 실패해도 계속 동작)
try {
    return objectMapper.readValue(cached, OrderResponse.class);
} catch (JsonProcessingException e) { ... }

// 2. throws 선언 (호출자에게 책임 넘김)
public OrderResponse getOrderManual(Long id) throws JsonProcessingException { ... }
```

캐시 실패해도 **DB 조회는 정상 진행**해야 하므로 `try-catch`가 맞다.

---

## 5. TTL 생략 시 위험

```java
// TTL 있음 (안전)
redisTemplate.opsForValue().set(cacheKey, json, Duration.ofMinutes(5));
// → 5분 후 자동 삭제

// TTL 없음 (위험)
redisTemplate.opsForValue().set(cacheKey, json);
// → Redis 서버가 꺼질 때까지 영구 보존
```

**문제 시나리오:**
```
1. getOrderManual(1) → status=PENDING → Redis 영구 저장
2. updateOrderStatus(1, FILLED) → DB 변경 → Redis 삭제 X (수동 구현이라 @CacheEvict 없음)
3. getOrderManual(1) 재호출 → Redis에 PENDING 영원히 반환 💥
```

**TTL = @CacheEvict를 빠뜨렸을 때의 마지막 안전망**

---

## 6. @Cacheable vs 수동 구현 비교

| | `@Cacheable` | 수동 구현 |
|--|---|---|
| 코드 양 | 어노테이션 1줄 | ~25줄 |
| 직렬화 | 자동 (`RedisCacheManager` 설정 사용) | 직접 처리 |
| TTL | `RedisCacheManager`에서 일괄 관리 | `set()` 호출 시 직접 지정 |
| 예외 처리 | 자동 | 직접 `try-catch` |
| 동작 원리 | **수동 구현과 완전히 동일** (AOP가 대신 실행) | — |

> `@Cacheable`은 프록시가 수동 구현 코드를 **대신 실행해주는 것**

---

## 7. 핵심 정리

| 개념 | 한 줄 요약 |
|------|----------|
| `withCacheConfiguration` | 캐시 이름별 TTL/설정 개별 지정 |
| Cache-Aside 4단계 | 요청 → 캐시 확인(Hit/Miss) → DB 조회 → 캐시 저장 |
| `readValue(json, Class)` | JSON 문자열 → Java 객체 (역직렬화) |
| `writeValueAsString(obj)` | Java 객체 → JSON 문자열 (직렬화) |
| TTL 생략 위험 | 영구 저장 → 오래된 데이터 무한 반환 |
| 체크 예외 | `JsonProcessingException` → `try-catch` 필수 |
