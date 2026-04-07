# Day 1 부록 — Kafka + Redis 설정 상세 (2026-04-06)

> Day 1에서 구성한 Kafka/Redis 설정의 각 코드가 왜 필요한지 상세 설명

---

## 1. 전체 구조에서 Kafka / Redis 위치

```
[POST /api/orders]
       ↓
 OrderService.createOrder()
       ↓
 orderRepository.save()        → MySQL 저장
       ↓
 OrderEventProducer.send()     → Kafka "order-events" 토픽 발행
       ↓
 OrderEventConsumer.consume()  ← Kafka 수신
       ↓
 WebSocket /topic/orders       → 프론트엔드 실시간 전송

[GET /api/orders/{id}]
       ↓
 @Cacheable → Redis 먼저 확인
       ↓ (캐시 없으면)
 orderRepository.findById()    → MySQL 조회 후 Redis에 저장
```

---

## 2. Kafka 설정

### application.yml — Kafka 연결 설정

```yaml
spring:
  kafka:
    bootstrap-servers: ${SPRING_KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    #                   ↑ Docker 환경변수          ↑ 로컬 개발 기본값

    consumer:
      group-id: order-group           # 컨슈머 그룹 이름
      auto-offset-reset: earliest     # 처음 구독 시 가장 오래된 메시지부터 읽음
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      properties:
        spring.json.trusted.packages: "com.order.*"  # 역직렬화 허용 패키지

    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer
```

**핵심 포인트:**

| 항목 | 설명 |
|------|------|
| `group-id` | 같은 그룹의 컨슈머들이 파티션을 나눠서 처리 |
| `auto-offset-reset: earliest` | 새 컨슈머가 처음 붙을 때 처음부터 읽음 (`latest`는 이후 메시지만 읽음) |
| `JsonDeserializer` | Kafka 메시지(bytes)를 Java 객체로 역직렬화 |
| `trusted.packages` | 보안상 역직렬화 허용할 패키지 명시 필수 |

---

### KafkaConfig.java — 토픽 자동 생성

```java
@Configuration
public class KafkaConfig {

    public static final String ORDER_TOPIC = "order-events";  // 상수로 관리

    @Bean
    public NewTopic orderTopic() {
        return TopicBuilder.name(ORDER_TOPIC)
                .partitions(3)   // 파티션 3개
                .replicas(1)     // 복제본 1개 (개발 환경)
                .build();
    }
}
```

**파티션(Partition)이란?**

```
order-events 토픽
├── Partition 0: [msg1] [msg4] [msg7] ...
├── Partition 1: [msg2] [msg5] [msg8] ...
└── Partition 2: [msg3] [msg6] [msg9] ...
```

- 토픽을 여러 파티션으로 나눠서 **병렬 처리** 가능
- 컨슈머 그룹 내 최대 병렬도 = 파티션 수
- 파티션 3 + 컨슈머 1 → 한 컨슈머가 3개 파티션 전부 처리
- 파티션 3 + 컨슈머 3 → 각 컨슈머가 파티션 1개씩 처리

**replicas(복제본):**

| 환경 | 권장 replica |
|------|-------------|
| 개발 | 1 (Kafka 브로커 1개) |
| 운영 | 3 (브로커 1개 장애나도 데이터 유지) |

**토픽 이름을 상수로 관리하는 이유:**
```java
public static final String ORDER_TOPIC = "order-events";
// → Producer, Consumer 모두 KafkaConfig.ORDER_TOPIC 참조
// → 오타 방지, 변경 시 한 곳만 수정
```

---

### OrderEvent.java — Kafka 이벤트 DTO

```java
@Getter
@Builder
@NoArgsConstructor   // Jackson 역직렬화에 필수
@AllArgsConstructor
public class OrderEvent {

    private Long orderId;
    private String customerName;
    private String productName;
    private Integer quantity;
    private BigDecimal totalPrice;
    private OrderStatus status;
    private LocalDateTime eventTime;

    // Order 엔티티 → OrderEvent 변환 (정적 팩토리)
    public static OrderEvent of(Order order) {
        return OrderEvent.builder()
                .orderId(order.getId())
                ...
                .eventTime(LocalDateTime.now())
                .build();
    }
}
```

**왜 Order 엔티티를 직접 쓰지 않고 OrderEvent를 별도로 만드나?**

| 이유 | 설명 |
|------|------|
| **직렬화 안전성** | JPA 엔티티는 Lazy Loading 등 복잡한 상태 → JSON 직렬화 시 문제 발생 가능 |
| **의존성 분리** | Kafka 이벤트 구조가 DB 스키마와 독립적으로 변경 가능 |
| **이벤트 전용 필드** | `eventTime` 같은 이벤트 시점 정보 추가 가능 |

**`@NoArgsConstructor` 가 필수인 이유:**
```
Kafka 메시지(JSON bytes) → Jackson이 역직렬화
→ 기본 생성자로 객체 생성 후 필드 주입
→ @NoArgsConstructor 없으면 역직렬화 실패!
```

---

### OrderEventProducer.java — 이벤트 발행

```java
@Component
@RequiredArgsConstructor
public class OrderEventProducer {

    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;
    //                           ↑ key   ↑ value

    public void sendOrderEvent(OrderEvent event) {
        kafkaTemplate.send(
                KafkaConfig.ORDER_TOPIC,          // 토픽명
                String.valueOf(event.getOrderId()), // 파티션 키 (같은 orderId → 같은 파티션)
                event                             // 메시지 본문
        )
        .whenComplete((result, ex) -> {            // 비동기 콜백
            if (ex == null) {
                log.info("발행 성공 — partition={}, offset={}",
                    result.getRecordMetadata().partition(),
                    result.getRecordMetadata().offset());
            } else {
                log.error("발행 실패", ex);
            }
        });
    }
}
```

**파티션 키(`orderId`)를 지정하는 이유:**
```
같은 orderId의 이벤트 → 항상 같은 파티션으로 전송
→ 같은 주문의 이벤트 순서 보장 (파티션 내 순서는 보장됨)

파티션 키 없으면 → 라운드로빈으로 분산
→ 같은 주문의 이벤트가 다른 파티션으로 가서 순서 뒤바뀔 수 있음
```

**`whenComplete` — 비동기 콜백:**
```java
kafkaTemplate.send(...)        // 즉시 반환 (비동기)
    .whenComplete((result, ex) -> {
        // 발행 완료되면 이 콜백이 호출됨
        // result: 성공 정보 (partition, offset)
        // ex: 실패 시 예외
    });
// → 메인 스레드는 블로킹 없이 계속 진행
```

---

### OrderEventConsumer.java — 이벤트 수신

```java
@Component
@RequiredArgsConstructor
public class OrderEventConsumer {

    private final SimpMessagingTemplate messagingTemplate;  // WebSocket 전송용

    @KafkaListener(
        topics = KafkaConfig.ORDER_TOPIC,  // 구독할 토픽
        groupId = "order-group"            // 컨슈머 그룹
    )
    public void consumeOrderEvent(OrderEvent event) {
        log.info("이벤트 수신 — orderId={}", event.getOrderId());

        // Kafka 수신 → WebSocket으로 실시간 전송
        messagingTemplate.convertAndSend("/topic/orders", event);
    }
}
```

**컨슈머 그룹의 역할:**
```
컨슈머 그룹 "order-group"
├── 컨슈머 인스턴스 A → Partition 0 전담
├── 컨슈머 인스턴스 B → Partition 1 전담
└── 컨슈머 인스턴스 C → Partition 2 전담

→ 스케일 아웃 시 컨슈머만 추가하면 자동으로 파티션 재분배됨
```

**오프셋(Offset)이란:**
```
Partition 0: [msg1:offset=0] [msg2:offset=1] [msg3:offset=2]
                                                      ↑
                                          컨슈머가 여기까지 읽었음을 Kafka에 기록
→ 컨슈머가 재시작해도 이어서 읽기 가능
```

---

## 3. Redis 설정

### application.yml — Redis 연결 설정

```yaml
spring:
  data:
    redis:
      host: ${SPRING_DATA_REDIS_HOST:localhost}
      port: ${SPRING_DATA_REDIS_PORT:6379}

  cache:
    type: redis   # Spring Cache 추상화 → Redis 사용
```

---

### RedisConfig.java — 직렬화 설정

```java
@Configuration
@EnableCaching   // @Cacheable, @CacheEvict 어노테이션 활성화
public class RedisConfig {

    // ① RedisTemplate — 직접 Redis 명령 실행 시 사용
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);

        StringRedisSerializer stringSerializer = new StringRedisSerializer();
        GenericJackson2JsonRedisSerializer jsonSerializer = new GenericJackson2JsonRedisSerializer();

        template.setKeySerializer(stringSerializer);    // key: String
        template.setValueSerializer(jsonSerializer);    // value: JSON
        template.setHashKeySerializer(stringSerializer);
        template.setHashValueSerializer(jsonSerializer);
        template.afterPropertiesSet();
        return template;
    }

    // ② RedisCacheManager — @Cacheable 어노테이션 기반 캐싱
    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(30))       // TTL 30분
                .serializeKeysWith(...)                  // key: String
                .serializeValuesWith(...)                // value: JSON
                .disableCachingNullValues();             // null은 캐싱 안 함

        return RedisCacheManager.builder(factory)
                .cacheDefaults(config)
                .build();
    }
}
```

**직렬화가 왜 필요한가?**
```
Java 객체 (OrderResponse)
    ↓ 직렬화 (Serialization)
Redis 저장 (bytes / JSON 문자열)
    ↓ 역직렬화 (Deserialization)
Java 객체 (OrderResponse)
```

**직렬화 방식 비교:**

| 방식 | 장점 | 단점 |
|------|------|------|
| `JdkSerializationRedisSerializer` (기본) | 별도 설정 불필요 | 바이너리라 Redis CLI로 읽기 불가, 타입 의존성 높음 |
| `GenericJackson2JsonRedisSerializer` | JSON이라 사람이 읽을 수 있음 | Jackson 의존 |
| `StringRedisSerializer` | 가장 단순 | String만 저장 가능 |

→ **실무에서는 JSON 직렬화 권장** (디버깅, 다른 언어 서비스 접근 가능)

---

### OrderService.java — @Cacheable / @CacheEvict

```java
// 단건 조회 — Redis 캐싱
@Cacheable(value = "orders", key = "#id")
public OrderResponse getOrder(Long id) {
    // Redis에 "orders::1" 키로 캐시 있으면 → DB 조회 안 함
    // 없으면 → DB 조회 후 Redis에 저장
    return OrderResponse.from(orderRepository.findById(id)...);
}

// 상태 변경 — 캐시 무효화
@CacheEvict(value = "orders", key = "#id")
public OrderResponse updateOrderStatus(Long id, OrderStatus status) {
    // DB 업데이트 후 Redis의 "orders::1" 키 삭제
    // → 다음 조회 시 캐시 미스 → 새로운 데이터 캐싱
}
```

**캐시 키 구조:**
```
Redis에 저장되는 키: "orders::1", "orders::2", ...
                      ↑ value명  ↑ id 값
```

**TTL(Time To Live):**
```
30분 후 자동 삭제 → DB와 Redis 데이터 불일치 최대 30분
→ 실시간성보다 성능이 중요한 데이터에 적합
→ 실시간성이 중요하면 @CacheEvict 적극 활용
```

---

## 4. Kafka vs Redis — 역할 비교

| | Kafka | Redis |
|---|---|---|
| **용도** | 이벤트 메시지 전달 (비동기) | 데이터 임시 저장 (캐싱) |
| **데이터 보존** | 설정한 기간 동안 유지 | TTL 만료 시 삭제 |
| **처리 방식** | Producer → 토픽 → Consumer | Set/Get (Key-Value) |
| **주요 사용처** | 서비스 간 이벤트 전달, 로그 수집 | 캐싱, 세션, 실시간 랭킹 |
| **이 프로젝트에서** | 주문 생성 이벤트 → WebSocket 전달 | 단건 주문 조회 캐싱 |

---

## 5. 실무에서 자주 쓰는 명령어

### Kafka (Kafdrop UI 대신 CLI)

```bash
# 컨테이너 접속
docker compose exec kafka bash

# 토픽 목록
kafka-topics --bootstrap-server localhost:9092 --list

# 토픽 상세 정보 (파티션 수, replicas)
kafka-topics --bootstrap-server localhost:9092 --describe --topic order-events

# 토픽 실시간 메시지 확인 (consume)
kafka-console-consumer --bootstrap-server localhost:9092 \
  --topic order-events --from-beginning

# 토픽 삭제
kafka-topics --bootstrap-server localhost:9092 --delete --topic order-events
```

### Redis CLI

```bash
# Redis 접속
docker compose exec redis redis-cli

# 전체 키 목록
KEYS *

# 특정 캐시 키 조회
GET "orders::1"

# 키 남은 TTL 확인
TTL "orders::1"

# 특정 키 삭제 (캐시 수동 초기화)
DEL "orders::1"

# 전체 캐시 삭제
FLUSHALL

# 저장된 데이터 타입 확인
TYPE "orders::1"
```

---

## 6. 개발 팁

### Kafka 메시지 순서 보장

```java
// 같은 orderId → 같은 파티션 → 순서 보장
kafkaTemplate.send(topic, String.valueOf(event.getOrderId()), event);
//                           ↑ 파티션 키

// 파티션 키 없으면 순서 보장 안 됨
kafkaTemplate.send(topic, event);  // ❌ 순서 보장 안 됨
```

### Redis 캐시 무효화 전략

```java
// ① 단건 무효화
@CacheEvict(value = "orders", key = "#id")

// ② 전체 무효화 (같은 캐시 이름 전체 삭제)
@CacheEvict(value = "orders", allEntries = true)

// ③ 저장 후 즉시 캐시 갱신
@CachePut(value = "orders", key = "#result.id")
// → 기존 캐시를 지우지 않고 업데이트된 값으로 교체
```

### Kafka 컨슈머 에러 처리

```java
@KafkaListener(topics = "order-events", groupId = "order-group")
public void consume(OrderEvent event) {
    try {
        process(event);
    } catch (Exception e) {
        // 예외 발생 시 기본 동작: 재시도 후 Dead Letter Topic으로 전송
        log.error("처리 실패", e);
        throw e; // 재시도 트리거
    }
}
```

### `@EnableCaching` 위치

```java
// 반드시 @Configuration 클래스에 선언
@Configuration
@EnableCaching  // ← 이게 없으면 @Cacheable 작동 안 함
public class RedisConfig { ... }
```

---

## 7. 참고 자료

| 주제 | URL |
|------|-----|
| Apache Kafka 공식 문서 | https://kafka.apache.org/documentation/ |
| Spring Kafka 레퍼런스 | https://docs.spring.io/spring-kafka/docs/current/reference/html/ |
| Spring Cache 추상화 | https://docs.spring.io/spring-framework/docs/current/reference/html/integration.html#cache |
| Spring Data Redis | https://docs.spring.io/spring-data/redis/docs/current/reference/html/ |
| Baeldung — Spring Kafka | https://www.baeldung.com/spring-kafka |
| Baeldung — Spring Redis 캐싱 | https://www.baeldung.com/spring-boot-redis-cache |
| Kafdrop GitHub | https://github.com/obsidiandynamics/kafdrop |
