#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 2: services/order-service 독립 실행 + Outbox Pattern
- backend/ 도메인 코드 → services/order-service/ (패키지: com.exchange.order)
- Outbox Pattern: OutboxEvent 저장 → 스케줄러가 Kafka 발행 (이중 쓰기 문제 해결)
- Strangler Fig: backend는 유지, order-service가 새로운 독립형 서비스
"""
import os

ROOT = r"d:\order-system"
SVC  = os.path.join(ROOT, "services", "order-service")
SRC  = os.path.join(SVC, "src", "main", "java", "com", "exchange", "order")
RES  = os.path.join(SVC, "src", "main", "resources")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK  {os.path.relpath(path, ROOT)}")

# ──────────────────────────────────────────────────────────────────
# 1. application.yml (order-service 전용 — port 8081)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(RES, "application.yml"), """\
spring:
  application:
    name: order-service

  datasource:
    url: ${SPRING_DATASOURCE_URL:jdbc:mysql://localhost:3306/orderdb?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC}
    username: ${SPRING_DATASOURCE_USERNAME:orderuser}
    password: ${SPRING_DATASOURCE_PASSWORD:orderpassword}
    driver-class-name: com.mysql.cj.jdbc.Driver

  jpa:
    hibernate:
      ddl-auto: update
    show-sql: false
    properties:
      hibernate:
        format_sql: false
        dialect: org.hibernate.dialect.MySQL8Dialect

  data:
    redis:
      host: ${SPRING_DATA_REDIS_HOST:localhost}
      port: ${SPRING_DATA_REDIS_PORT:6379}

  cache:
    type: redis

  kafka:
    bootstrap-servers: ${SPRING_KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    consumer:
      group-id: order-service-group
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.springframework.kafka.support.serializer.JsonDeserializer
      properties:
        spring.json.trusted.packages: "com.exchange.order.*,com.exchange.common.*"
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.springframework.kafka.support.serializer.JsonSerializer

server:
  port: 8081

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics
  endpoint:
    health:
      show-details: always

springdoc:
  swagger-ui:
    path: /swagger-ui.html
  api-docs:
    path: /api-docs

logging:
  level:
    com.exchange.order: DEBUG
    org.springframework.kafka: WARN

# Outbox 스케줄러 설정
outbox:
  scheduler:
    fixed-delay-ms: 5000   # 5초마다 미발행 이벤트 재시도
    max-retry: 5            # 최대 재시도 횟수
""")

# ──────────────────────────────────────────────────────────────────
# 2. OrderServiceApplication.java
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "OrderServiceApplication.java"), """\
package com.exchange.order;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Order Service — 마이크로서비스 독립 실행 진입점
 * - Port: 8081
 * - Outbox Pattern으로 Kafka 발행 신뢰성 보장
 */
@SpringBootApplication
@EnableAsync
@EnableScheduling
public class OrderServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 3. 공통 응답/예외
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "common", "response", "ApiResponse.java"), """\
package com.exchange.order.common.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Getter;

@Getter
@JsonInclude(JsonInclude.Include.NON_NULL)
public class ApiResponse<T> {
    private final boolean success;
    private final String message;
    private final T data;

    private ApiResponse(boolean success, String message, T data) {
        this.success = success;
        this.message = message;
        this.data = data;
    }

    public static <T> ApiResponse<T> success(T data) {
        return new ApiResponse<>(true, "성공", data);
    }

    public static <T> ApiResponse<T> success(String message, T data) {
        return new ApiResponse<>(true, message, data);
    }

    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, message, null);
    }
}
""")

write(os.path.join(SRC, "common", "exception", "GlobalExceptionHandler.java"), """\
package com.exchange.order.common.exception;

import com.exchange.order.common.response.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgument(IllegalArgumentException e) {
        log.warn("[비즈니스 오류] {}", e.getMessage());
        return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
    }

    @ExceptionHandler(IllegalStateException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalState(IllegalStateException e) {
        log.warn("[상태 오류] {}", e.getMessage());
        return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleValidation(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(fe -> fe.getField() + ": " + fe.getDefaultMessage())
                .findFirst().orElse("유효성 검사 실패");
        return ResponseEntity.badRequest().body(ApiResponse.error(message));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneral(Exception e) {
        log.error("[서버 오류]", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error("서버 내부 오류가 발생했습니다."));
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 4. 도메인 Entity
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "entity", "OrderType.java"), """\
package com.exchange.order.domain.order.entity;

public enum OrderType {
    MARKET,     // 시장가 주문 — 즉시 체결, 가격 지정 없음
    LIMIT,      // 지정가 주문 — 지정가 이하/이상에서만 체결
    STOP_LOSS,  // 손절 주문 — 트리거 가격 도달 시 시장가로 전환
    STOP_LIMIT  // 스탑-리밋 — 트리거 가격 도달 시 지정가로 전환
}
""")

write(os.path.join(SRC, "domain", "order", "entity", "OrderStatus.java"), """\
package com.exchange.order.domain.order.entity;

import java.util.Set;
import java.util.EnumSet;

/**
 * 주문 상태 State Machine
 * canTransitionTo()로 잘못된 상태 전이를 사전 차단
 */
public enum OrderStatus {
    PENDING {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.of(PROCESSING, CANCELLED);
        }
    },
    PROCESSING {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.of(COMPLETED, CANCELLED);
        }
    },
    COMPLETED {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.noneOf(OrderStatus.class);
        }
    },
    CANCELLED {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.noneOf(OrderStatus.class);
        }
    };

    public abstract Set<OrderStatus> allowedTransitions();

    public boolean canTransitionTo(OrderStatus next) {
        return allowedTransitions().contains(next);
    }

    public boolean isTerminal() {
        return this == COMPLETED || this == CANCELLED;
    }
}
""")

write(os.path.join(SRC, "domain", "order", "entity", "Order.java"), """\
package com.exchange.order.domain.order.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "orders")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 50)
    private String customerName;

    @Column(nullable = false, length = 100)
    private String productName;

    @Column(nullable = false)
    private Integer quantity;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal totalPrice;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private OrderType orderType = OrderType.LIMIT;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OrderStatus status;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    /**
     * State Machine 기반 상태 전이 — 잘못된 전이 즉시 예외
     */
    public void updateStatus(OrderStatus newStatus) {
        if (!this.status.canTransitionTo(newStatus)) {
            throw new IllegalStateException(
                String.format("주문 상태 전이 불가: %s → %s", this.status, newStatus));
        }
        this.status = newStatus;
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 5. Outbox Pattern 핵심 — OutboxEvent 엔티티
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "outbox", "entity", "OutboxEvent.java"), """\
package com.exchange.order.domain.outbox.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * Outbox Pattern — 이벤트를 DB에 먼저 저장
 *
 * [왜 Outbox Pattern인가?]
 * 기존: DB 저장 성공 → Kafka 발행 (비동기) → Kafka 실패 시 이벤트 소실
 * 개선: DB 저장 + OutboxEvent 저장 (단일 트랜잭션) → 스케줄러가 안전하게 Kafka 발행
 *
 * 보장: DB 커밋 = 이벤트 저장 보장 → 최소 1회 발행(at-least-once) 달성
 */
@Entity
@Table(name = "outbox_events",
       indexes = {
           @Index(name = "idx_outbox_status_created", columnList = "status, createdAt"),
           @Index(name = "idx_outbox_aggregate", columnList = "aggregateType, aggregateId")
       })
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Builder
@AllArgsConstructor
public class OutboxEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 집합체 타입 (예: "Order") */
    @Column(nullable = false, length = 50)
    private String aggregateType;

    /** 집합체 ID (주문 ID) */
    @Column(nullable = false)
    private Long aggregateId;

    /** 이벤트 타입 (예: "ORDER_CREATED", "ORDER_STATUS_CHANGED") */
    @Column(nullable = false, length = 100)
    private String eventType;

    /** JSON 직렬화된 이벤트 페이로드 */
    @Column(nullable = false, columnDefinition = "TEXT")
    private String payload;

    /** Kafka 토픽 */
    @Column(nullable = false, length = 100)
    private String topic;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private OutboxStatus status = OutboxStatus.PENDING;

    /** 재시도 횟수 */
    @Column(nullable = false)
    @Builder.Default
    private int retryCount = 0;

    /** 마지막 오류 메시지 */
    @Column(length = 500)
    private String lastError;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    private LocalDateTime publishedAt;

    public void markPublished() {
        this.status = OutboxStatus.PUBLISHED;
        this.publishedAt = LocalDateTime.now();
    }

    public void markFailed(String errorMessage) {
        this.retryCount++;
        this.lastError = errorMessage;
        if (this.retryCount >= 5) {
            this.status = OutboxStatus.DEAD_LETTER;
        }
        // PENDING 유지 — 다음 스케줄러 실행 시 재시도
    }
}
""")

write(os.path.join(SRC, "domain", "outbox", "entity", "OutboxStatus.java"), """\
package com.exchange.order.domain.outbox.entity;

public enum OutboxStatus {
    PENDING,     // 발행 대기
    PUBLISHED,   // 발행 완료
    DEAD_LETTER  // 최대 재시도 초과 — 수동 개입 필요
}
""")

# ──────────────────────────────────────────────────────────────────
# 6. Outbox Repository
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "outbox", "repository", "OutboxEventRepository.java"), """\
package com.exchange.order.domain.outbox.repository;

import com.exchange.order.domain.outbox.entity.OutboxEvent;
import com.exchange.order.domain.outbox.entity.OutboxStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface OutboxEventRepository extends JpaRepository<OutboxEvent, Long> {

    /**
     * PENDING 상태 중 재시도 횟수 5회 미만인 이벤트만 조회
     * 생성 시각 순 정렬 — FIFO 처리
     */
    @Query("SELECT o FROM OutboxEvent o WHERE o.status = :status AND o.retryCount < :maxRetry ORDER BY o.createdAt ASC")
    List<OutboxEvent> findPendingEvents(
            @Param("status") OutboxStatus status,
            @Param("maxRetry") int maxRetry);
}
""")

# ──────────────────────────────────────────────────────────────────
# 7. Outbox 스케줄러 (Relay)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "outbox", "scheduler", "OutboxEventPublisher.java"), """\
package com.exchange.order.domain.outbox.scheduler;

import com.exchange.order.domain.outbox.entity.OutboxEvent;
import com.exchange.order.domain.outbox.entity.OutboxStatus;
import com.exchange.order.domain.outbox.repository.OutboxEventRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Outbox Pattern — Relay 스케줄러
 *
 * 동작 흐름:
 * 1. PENDING 상태의 OutboxEvent 조회
 * 2. Kafka에 발행 시도
 * 3. 성공 → PUBLISHED 마킹
 * 4. 실패 → retryCount++ (5회 초과 시 DEAD_LETTER)
 *
 * @Transactional: Kafka 발행 결과가 DB에 원자적으로 반영
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxEventPublisher {

    private final OutboxEventRepository outboxEventRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Value("${outbox.scheduler.max-retry:5}")
    private int maxRetry;

    @Scheduled(fixedDelayString = "${outbox.scheduler.fixed-delay-ms:5000}")
    @Transactional
    public void publishPendingEvents() {
        List<OutboxEvent> pendingEvents =
                outboxEventRepository.findPendingEvents(OutboxStatus.PENDING, maxRetry);

        if (pendingEvents.isEmpty()) return;

        log.debug("[Outbox] 발행 대상 이벤트 {}건 처리 시작", pendingEvents.size());

        for (OutboxEvent event : pendingEvents) {
            try {
                kafkaTemplate.send(event.getTopic(),
                                   String.valueOf(event.getAggregateId()),
                                   event.getPayload())
                        .get(); // 동기 대기 — 발행 확인 보장

                event.markPublished();
                log.info("[Outbox] 발행 완료 — id={}, type={}, aggregateId={}",
                        event.getId(), event.getEventType(), event.getAggregateId());
            } catch (Exception e) {
                event.markFailed(e.getMessage());
                log.error("[Outbox] 발행 실패 — id={}, retry={}, error={}",
                        event.getId(), event.getRetryCount(), e.getMessage());
            }
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 8. Outbox 저장 서비스
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "outbox", "service", "OutboxService.java"), """\
package com.exchange.order.domain.outbox.service;

import com.exchange.order.domain.outbox.entity.OutboxEvent;
import com.exchange.order.domain.outbox.repository.OutboxEventRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * OutboxEvent 저장을 담당하는 서비스
 * — 반드시 OrderCommandService와 동일 트랜잭션에서 호출
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OutboxService {

    private final OutboxEventRepository outboxEventRepository;
    private final ObjectMapper objectMapper;

    public void save(String aggregateType, Long aggregateId,
                     String eventType, String topic, Object payload) {
        try {
            String json = objectMapper.writeValueAsString(payload);
            OutboxEvent outboxEvent = OutboxEvent.builder()
                    .aggregateType(aggregateType)
                    .aggregateId(aggregateId)
                    .eventType(eventType)
                    .topic(topic)
                    .payload(json)
                    .build();
            outboxEventRepository.save(outboxEvent);
            log.debug("[Outbox] 이벤트 저장 — type={}, aggregateId={}", eventType, aggregateId);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Outbox 이벤트 직렬화 실패: " + eventType, e);
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 9. Kafka Config
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "config", "KafkaConfig.java"), """\
package com.exchange.order.config;

import org.apache.kafka.clients.producer.ProducerConfig;
import org.apache.kafka.common.serialization.StringSerializer;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.kafka.core.*;

import java.util.HashMap;
import java.util.Map;

/**
 * Outbox Pattern용 KafkaTemplate<String, String>
 * — 페이로드가 이미 JSON String이므로 StringSerializer 사용
 */
@Configuration
public class KafkaConfig {

    public static final String ORDER_TOPIC = "order-events";
    public static final String ORDER_STATUS_TOPIC = "order-status-events";

    @Value("${spring.kafka.bootstrap-servers}")
    private String bootstrapServers;

    @Bean
    public ProducerFactory<String, String> producerFactory() {
        Map<String, Object> config = new HashMap<>();
        config.put(ProducerConfig.BOOTSTRAP_SERVERS_CONFIG, bootstrapServers);
        config.put(ProducerConfig.KEY_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        config.put(ProducerConfig.VALUE_SERIALIZER_CLASS_CONFIG, StringSerializer.class);
        // 신뢰성: acks=all, 재시도 3회
        config.put(ProducerConfig.ACKS_CONFIG, "all");
        config.put(ProducerConfig.RETRIES_CONFIG, 3);
        config.put(ProducerConfig.ENABLE_IDEMPOTENCE_CONFIG, true);
        return new DefaultKafkaProducerFactory<>(config);
    }

    @Bean
    public KafkaTemplate<String, String> kafkaTemplate() {
        return new KafkaTemplate<>(producerFactory());
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 10. Redis Config
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "config", "RedisConfig.java"), """\
package com.exchange.order.config;

import org.springframework.cache.annotation.EnableCaching;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.cache.RedisCacheConfiguration;
import org.springframework.data.redis.cache.RedisCacheManager;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.RedisSerializationContext;
import org.springframework.data.redis.serializer.StringRedisSerializer;

import java.time.Duration;

@EnableCaching
@Configuration
public class RedisConfig {

    @Bean
    public RedisCacheManager cacheManager(RedisConnectionFactory factory) {
        RedisCacheConfiguration config = RedisCacheConfiguration.defaultCacheConfig()
                .entryTtl(Duration.ofMinutes(10))
                .serializeKeysWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new StringRedisSerializer()))
                .serializeValuesWith(RedisSerializationContext.SerializationPair
                        .fromSerializer(new GenericJackson2JsonRedisSerializer()));

        return RedisCacheManager.builder(factory).cacheDefaults(config).build();
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 11. Order 도메인 — DTO
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "dto", "OrderRequest.java"), """\
package com.exchange.order.domain.order.dto;

import com.exchange.order.domain.order.entity.OrderType;
import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.math.BigDecimal;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrderRequest {

    @NotBlank(message = "고객명은 필수입니다")
    @Size(max = 50, message = "고객명은 50자 이하여야 합니다")
    private String customerName;

    @NotBlank(message = "상품명은 필수입니다")
    @Size(max = 100, message = "상품명은 100자 이하여야 합니다")
    private String productName;

    @NotNull(message = "수량은 필수입니다")
    @Positive(message = "수량은 양수여야 합니다")
    @Max(value = 10000, message = "수량은 10,000 이하여야 합니다")
    private Integer quantity;

    @NotNull(message = "총 금액은 필수입니다")
    @Positive(message = "총 금액은 양수여야 합니다")
    @DecimalMax(value = "1000000000", message = "금액은 10억 이하여야 합니다")
    private BigDecimal totalPrice;

    private OrderType orderType;
}
""")

write(os.path.join(SRC, "domain", "order", "dto", "OrderResponse.java"), """\
package com.exchange.order.domain.order.dto;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.entity.OrderType;
import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Builder
public class OrderResponse {
    private Long id;
    private String customerName;
    private String productName;
    private Integer quantity;
    private BigDecimal totalPrice;
    private OrderType orderType;
    private OrderStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static OrderResponse from(Order order) {
        return OrderResponse.builder()
                .id(order.getId())
                .customerName(order.getCustomerName())
                .productName(order.getProductName())
                .quantity(order.getQuantity())
                .totalPrice(order.getTotalPrice())
                .orderType(order.getOrderType())
                .status(order.getStatus())
                .createdAt(order.getCreatedAt())
                .updatedAt(order.getUpdatedAt())
                .build();
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 12. Port 인터페이스 (DIP)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "port", "OrderQueryPort.java"), """\
package com.exchange.order.domain.order.port;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;

import java.util.List;
import java.util.Optional;

public interface OrderQueryPort {
    Optional<Order> findById(Long id);
    List<Order> findAll();
    List<Order> findByStatus(OrderStatus status);
    List<Order> findByCustomerName(String customerName);
}
""")

write(os.path.join(SRC, "domain", "order", "port", "OrderCommandPort.java"), """\
package com.exchange.order.domain.order.port;

import com.exchange.order.domain.order.entity.Order;

public interface OrderCommandPort {
    Order save(Order order);
    void deleteById(Long id);
}
""")

# ──────────────────────────────────────────────────────────────────
# 13. Repository
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "repository", "OrderRepository.java"), """\
package com.exchange.order.domain.order.repository;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByStatus(OrderStatus status);
    List<Order> findByCustomerName(String customerName);
}
""")

write(os.path.join(SRC, "domain", "order", "repository", "OrderRepositoryAdapter.java"), """\
package com.exchange.order.domain.order.repository;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.port.OrderCommandPort;
import com.exchange.order.domain.order.port.OrderQueryPort;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;

/**
 * Hexagonal Architecture — Repository Adapter
 * DIP: 서비스는 Port 인터페이스에만 의존, 구현체(JPA)는 여기에만 위치
 */
@Component
@RequiredArgsConstructor
public class OrderRepositoryAdapter implements OrderQueryPort, OrderCommandPort {

    private final OrderRepository orderRepository;

    @Override public Optional<Order> findById(Long id)            { return orderRepository.findById(id); }
    @Override public List<Order> findAll()                        { return orderRepository.findAll(); }
    @Override public List<Order> findByStatus(OrderStatus status) { return orderRepository.findByStatus(status); }
    @Override public List<Order> findByCustomerName(String name)  { return orderRepository.findByCustomerName(name); }
    @Override public Order save(Order order)                      { return orderRepository.save(order); }
    @Override public void deleteById(Long id)                     { orderRepository.deleteById(id); }
}
""")

# ──────────────────────────────────────────────────────────────────
# 14. Validator (Chain of Responsibility)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "validator", "OrderValidator.java"), """\
package com.exchange.order.domain.order.validator;

import com.exchange.order.domain.order.dto.OrderRequest;

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
""")

write(os.path.join(SRC, "domain", "order", "validator", "QuantityValidator.java"), """\
package com.exchange.order.domain.order.validator;

import com.exchange.order.domain.order.dto.OrderRequest;
import org.springframework.stereotype.Component;

@Component
public class QuantityValidator implements OrderValidator {
    private static final int MAX_QUANTITY = 10_000;

    @Override
    public void validate(OrderRequest request) {
        if (request.getQuantity() == null || request.getQuantity() <= 0) {
            throw new IllegalArgumentException("수량은 1 이상이어야 합니다.");
        }
        if (request.getQuantity() > MAX_QUANTITY) {
            throw new IllegalArgumentException("수량은 " + MAX_QUANTITY + " 이하여야 합니다.");
        }
    }
}
""")

write(os.path.join(SRC, "domain", "order", "validator", "PriceValidator.java"), """\
package com.exchange.order.domain.order.validator;

import com.exchange.order.domain.order.dto.OrderRequest;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
public class PriceValidator implements OrderValidator {
    private static final BigDecimal MAX_PRICE = new BigDecimal("1000000000");

    @Override
    public void validate(OrderRequest request) {
        if (request.getTotalPrice() == null || request.getTotalPrice().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("금액은 0보다 커야 합니다.");
        }
        if (request.getTotalPrice().compareTo(MAX_PRICE) > 0) {
            throw new IllegalArgumentException("금액은 10억 이하여야 합니다.");
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 15. Strategy Pattern
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "strategy", "OrderStrategy.java"), """\
package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;

public interface OrderStrategy {
    OrderType getSupportedType();
    void validate(OrderRequest request);

    default void preProcess(OrderRequest request) {}
    default void postProcess(Long orderId) {}
}
""")

write(os.path.join(SRC, "domain", "order", "strategy", "MarketOrderStrategy.java"), """\
package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class MarketOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getSupportedType() { return OrderType.MARKET; }

    @Override
    public void validate(OrderRequest request) {
        // 시장가 주문: 가격은 Trading Engine이 결정하므로 별도 검증 없음
        log.debug("[MarketOrder] 시장가 주문 검증 통과 — qty={}", request.getQuantity());
    }

    @Override
    public void postProcess(Long orderId) {
        log.info("[MarketOrder] 시장가 즉시 체결 요청 전송 — orderId={}", orderId);
    }
}
""")

write(os.path.join(SRC, "domain", "order", "strategy", "LimitOrderStrategy.java"), """\
package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class LimitOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getSupportedType() { return OrderType.LIMIT; }

    @Override
    public void validate(OrderRequest request) {
        if (request.getTotalPrice() == null) {
            throw new IllegalArgumentException("지정가 주문은 가격이 필수입니다.");
        }
        log.debug("[LimitOrder] 지정가 주문 검증 통과 — price={}", request.getTotalPrice());
    }
}
""")

write(os.path.join(SRC, "domain", "order", "strategy", "OrderStrategyFactory.java"), """\
package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Factory Pattern — Spring DI로 모든 OrderStrategy 구현체 자동 수집
 * OCP: 새 주문 타입 추가 시 Strategy 클래스만 추가하면 자동 등록
 */
@Slf4j
@Component
public class OrderStrategyFactory {

    private final Map<OrderType, OrderStrategy> strategies;

    public OrderStrategyFactory(List<OrderStrategy> strategyList) {
        this.strategies = strategyList.stream()
                .collect(Collectors.toMap(OrderStrategy::getSupportedType, s -> s));
        log.info("[StrategyFactory] 등록된 전략: {}", strategies.keySet());
    }

    public OrderStrategy getStrategy(OrderType type) {
        OrderStrategy strategy = strategies.get(type);
        if (strategy == null) {
            throw new IllegalArgumentException("지원하지 않는 주문 타입: " + type);
        }
        return strategy;
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 16. 도메인 이벤트 (Spring ApplicationEvent)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "event", "OrderCreatedEvent.java"), """\
package com.exchange.order.domain.order.event;

import com.exchange.order.domain.order.entity.Order;
import lombok.Getter;
import org.springframework.context.ApplicationEvent;

@Getter
public class OrderCreatedEvent extends ApplicationEvent {
    private final Long orderId;
    private final String customerName;
    private final String productName;
    private final String aggregateType = "Order";

    public OrderCreatedEvent(Object source, Order order) {
        super(source);
        this.orderId = order.getId();
        this.customerName = order.getCustomerName();
        this.productName = order.getProductName();
    }
}
""")

write(os.path.join(SRC, "domain", "order", "event", "OrderStatusChangedEvent.java"), """\
package com.exchange.order.domain.order.event;

import com.exchange.order.domain.order.entity.OrderStatus;
import lombok.Getter;
import org.springframework.context.ApplicationEvent;

@Getter
public class OrderStatusChangedEvent extends ApplicationEvent {
    private final Long orderId;
    private final OrderStatus previousStatus;
    private final OrderStatus newStatus;

    public OrderStatusChangedEvent(Object source, Long orderId,
                                   OrderStatus previousStatus, OrderStatus newStatus) {
        super(source);
        this.orderId = orderId;
        this.previousStatus = previousStatus;
        this.newStatus = newStatus;
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 17. CQRS — Command Service (Outbox 통합)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "service", "command", "OrderCommandService.java"), """\
package com.exchange.order.domain.order.service.command;

import com.exchange.order.config.KafkaConfig;
import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.dto.OrderResponse;
import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.entity.OrderType;
import com.exchange.order.domain.order.event.OrderCreatedEvent;
import com.exchange.order.domain.order.event.OrderStatusChangedEvent;
import com.exchange.order.domain.order.port.OrderCommandPort;
import com.exchange.order.domain.order.port.OrderQueryPort;
import com.exchange.order.domain.order.strategy.OrderStrategy;
import com.exchange.order.domain.order.strategy.OrderStrategyFactory;
import com.exchange.order.domain.order.validator.OrderValidator;
import com.exchange.order.domain.outbox.service.OutboxService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Map;

/**
 * [CQRS Command 측] 주문 생성/수정/삭제
 *
 * Outbox Pattern 통합:
 * - 주문 저장 + OutboxEvent 저장을 단일 @Transactional로 묶음
 * - Kafka 직접 발행 제거 → OutboxEventPublisher(스케줄러)가 담당
 * - 이중 쓰기 문제 완전 해소
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class OrderCommandService {

    private final OrderCommandPort orderCommandPort;
    private final OrderQueryPort orderQueryPort;
    private final OrderStrategyFactory strategyFactory;
    private final OrderValidator orderValidator;
    private final ApplicationEventPublisher eventPublisher;
    private final OutboxService outboxService;

    public OrderResponse createOrder(OrderRequest request) {
        // 1. 검증 체인
        orderValidator.validate(request);

        // 2. 전략 선택
        OrderType orderType = request.getOrderType() != null ? request.getOrderType() : OrderType.LIMIT;
        OrderStrategy strategy = strategyFactory.getStrategy(orderType);
        strategy.validate(request);
        strategy.preProcess(request);

        // 3. 주문 저장
        Order order = Order.builder()
                .customerName(request.getCustomerName())
                .productName(request.getProductName())
                .quantity(request.getQuantity())
                .totalPrice(request.getTotalPrice())
                .orderType(orderType)
                .status(OrderStatus.PENDING)
                .build();
        Order savedOrder = orderCommandPort.save(order);

        // 4. Outbox 이벤트 저장 (같은 트랜잭션 — 원자성 보장)
        Map<String, Object> payload = Map.of(
            "orderId", savedOrder.getId(),
            "customerName", savedOrder.getCustomerName(),
            "productName", savedOrder.getProductName(),
            "quantity", savedOrder.getQuantity(),
            "totalPrice", savedOrder.getTotalPrice(),
            "orderType", savedOrder.getOrderType(),
            "status", savedOrder.getStatus()
        );
        outboxService.save("Order", savedOrder.getId(),
                "ORDER_CREATED", KafkaConfig.ORDER_TOPIC, payload);

        // 5. Spring 도메인 이벤트 (동기, 내부용)
        eventPublisher.publishEvent(new OrderCreatedEvent(this, savedOrder));
        strategy.postProcess(savedOrder.getId());

        log.info("[주문 생성] orderId={}, type={}", savedOrder.getId(), orderType);
        return OrderResponse.from(savedOrder);
    }

    @CacheEvict(value = "orders", key = "#id")
    public OrderResponse updateOrderStatus(Long id, OrderStatus newStatus) {
        Order order = orderQueryPort.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));

        OrderStatus previousStatus = order.getStatus();
        order.updateStatus(newStatus);
        Order updated = orderCommandPort.save(order);

        // Outbox: 상태 변경 이벤트
        outboxService.save("Order", id, "ORDER_STATUS_CHANGED",
                KafkaConfig.ORDER_STATUS_TOPIC,
                Map.of("orderId", id, "from", previousStatus, "to", newStatus));

        eventPublisher.publishEvent(
                new OrderStatusChangedEvent(this, id, previousStatus, newStatus));

        log.info("[상태 변경] orderId={}, {} → {}", id, previousStatus, newStatus);
        return OrderResponse.from(updated);
    }

    @CacheEvict(value = "orders", key = "#id")
    public void deleteOrder(Long id) {
        orderQueryPort.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
        orderCommandPort.deleteById(id);
        log.info("[주문 삭제] orderId={}", id);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 18. CQRS — Query Service
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "service", "query", "OrderQueryService.java"), """\
package com.exchange.order.domain.order.service.query;

import com.exchange.order.domain.order.dto.OrderResponse;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.port.OrderQueryPort;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * [CQRS Query 측] 주문 조회 전용 — @Cacheable Redis 캐싱 적용
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderQueryService {

    private final OrderQueryPort orderQueryPort;

    @Cacheable(value = "orders", key = "#id")
    public OrderResponse getOrder(Long id) {
        return orderQueryPort.findById(id)
                .map(OrderResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
    }

    public List<OrderResponse> getAllOrders() {
        return orderQueryPort.findAll().stream()
                .map(OrderResponse::from)
                .toList();
    }

    public List<OrderResponse> getOrdersByStatus(OrderStatus status) {
        return orderQueryPort.findByStatus(status).stream()
                .map(OrderResponse::from)
                .toList();
    }

    public List<OrderResponse> getOrdersByCustomer(String customerName) {
        return orderQueryPort.findByCustomerName(customerName).stream()
                .map(OrderResponse::from)
                .toList();
    }

    /** 상태별 집계 통계 */
    public Map<OrderStatus, Long> getOrderStatsByStatus() {
        return orderQueryPort.findAll().stream()
                .collect(Collectors.groupingBy(
                        o -> o.getStatus(),
                        Collectors.counting()));
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 19. Kafka Consumer
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "kafka", "consumer", "OrderEventConsumer.java"), """\
package com.exchange.order.kafka.consumer;

import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/**
 * Kafka Consumer — 다른 서비스에서 발행한 이벤트 수신
 * (Phase 3-5에서 account-service, trading-engine 이벤트 수신)
 */
@Slf4j
@Component
public class OrderEventConsumer {

    @KafkaListener(topics = "order-events", groupId = "order-service-group")
    public void consume(String message) {
        log.info("[Kafka Consumer] 이벤트 수신: {}", message);
        // Phase 3 이후 구체적 처리 로직 추가 예정
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 20. REST Controller
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "order", "controller", "OrderController.java"), """\
package com.exchange.order.domain.order.controller;

import com.exchange.order.common.response.ApiResponse;
import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.dto.OrderResponse;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.service.command.OrderCommandService;
import com.exchange.order.domain.order.service.query.OrderQueryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@Tag(name = "Order API", description = "주문 생성/조회/상태 관리")
@RestController
@RequestMapping("/api/v1/orders")
@RequiredArgsConstructor
public class OrderController {

    private final OrderCommandService commandService;
    private final OrderQueryService queryService;

    @Operation(summary = "주문 생성")
    @PostMapping
    public ResponseEntity<ApiResponse<OrderResponse>> createOrder(
            @Valid @RequestBody OrderRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success("주문이 생성되었습니다.", commandService.createOrder(request)));
    }

    @Operation(summary = "주문 단건 조회")
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<OrderResponse>> getOrder(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrder(id)));
    }

    @Operation(summary = "전체 주문 목록 조회")
    @GetMapping
    public ResponseEntity<ApiResponse<List<OrderResponse>>> getAllOrders() {
        return ResponseEntity.ok(ApiResponse.success(queryService.getAllOrders()));
    }

    @Operation(summary = "상태별 주문 조회")
    @GetMapping("/status/{status}")
    public ResponseEntity<ApiResponse<List<OrderResponse>>> getOrdersByStatus(
            @PathVariable OrderStatus status) {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrdersByStatus(status)));
    }

    @Operation(summary = "고객별 주문 조회")
    @GetMapping("/customer/{customerName}")
    public ResponseEntity<ApiResponse<List<OrderResponse>>> getOrdersByCustomer(
            @PathVariable String customerName) {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrdersByCustomer(customerName)));
    }

    @Operation(summary = "주문 상태 변경")
    @PatchMapping("/{id}/status")
    public ResponseEntity<ApiResponse<OrderResponse>> updateStatus(
            @PathVariable Long id,
            @RequestParam OrderStatus status) {
        return ResponseEntity.ok(ApiResponse.success(commandService.updateOrderStatus(id, status)));
    }

    @Operation(summary = "주문 삭제")
    @DeleteMapping("/{id}")
    public ResponseEntity<ApiResponse<Void>> deleteOrder(@PathVariable Long id) {
        commandService.deleteOrder(id);
        return ResponseEntity.ok(ApiResponse.success(null));
    }

    @Operation(summary = "상태별 주문 통계")
    @GetMapping("/stats")
    public ResponseEntity<ApiResponse<Map<OrderStatus, Long>>> getStats() {
        return ResponseEntity.ok(ApiResponse.success(queryService.getOrderStatsByStatus()));
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 21. Validator Config (Bean 조립)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "config", "OrderValidatorConfig.java"), """\
package com.exchange.order.config;

import com.exchange.order.domain.order.validator.OrderValidator;
import com.exchange.order.domain.order.validator.PriceValidator;
import com.exchange.order.domain.order.validator.QuantityValidator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Chain of Responsibility 조립
 * 새 검증 규칙 추가 시 여기서 .andThen() 체인만 연결
 */
@Configuration
public class OrderValidatorConfig {

    @Bean
    public OrderValidator orderValidator(QuantityValidator quantityValidator,
                                         PriceValidator priceValidator) {
        return quantityValidator.andThen(priceValidator);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 22. build.gradle.kts 업데이트 (ObjectMapper Bean 자동 등록용 jackson 추가)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SVC, "build.gradle.kts"), """\
plugins {
    java
    id("org.springframework.boot") version "3.2.3"
    id("io.spring.dependency-management") version "1.1.4"
}

group = "com.exchange"
version = "0.0.1-SNAPSHOT"

java { sourceCompatibility = JavaVersion.VERSION_17 }

repositories { mavenCentral() }

dependencies {
    // Web + Validation
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")

    // JPA + MySQL
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    runtimeOnly("com.mysql:mysql-connector-j")

    // Redis Cache
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-cache")

    // Kafka
    implementation("org.springframework.kafka:spring-kafka")

    // Jackson (ObjectMapper Bean — Outbox 직렬화)
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")

    // Swagger
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0")

    // Lombok
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")

    // Test
    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
}

tasks.withType<Test> { useJUnitPlatform() }
""")

print()
print("=== Phase 2 생성 완료 ===")
print("서비스: services/order-service")
print("Outbox 관련 파일:")
print("  - domain/outbox/entity/OutboxEvent.java")
print("  - domain/outbox/entity/OutboxStatus.java")
print("  - domain/outbox/repository/OutboxEventRepository.java")
print("  - domain/outbox/service/OutboxService.java")
print("  - domain/outbox/scheduler/OutboxEventPublisher.java")
print("다음: ./gradlew.bat :services:order-service:compileJava")
