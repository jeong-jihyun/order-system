#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 4: market-data-service
- STOMP over WebSocket: 실시간 시세 브로드캐스팅 (/topic/ticker/{symbol})
- Redis Pub/Sub: 멀티 인스턴스 간 시세 동기화
- OHLCV 캔들 데이터 (Redis ZSet 저장 + REST 조회)
- Kafka Consumer: order-events → 체결 가격 업데이트
- Port: 8083
"""
import os

ROOT = r"d:\order-system"
MDS  = os.path.join(ROOT, "services", "market-data-service")
SRC  = os.path.join(MDS, "src", "main", "java", "com", "exchange", "marketdata")
RES  = os.path.join(MDS, "src", "main", "resources")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK  {os.path.relpath(path, ROOT)}")

# ──────────────────────────────────────────────────────────────────
# 1. build.gradle.kts
# ──────────────────────────────────────────────────────────────────
write(os.path.join(MDS, "build.gradle.kts"), """\
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
    // Web
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")

    // WebSocket (STOMP)
    implementation("org.springframework.boot:spring-boot-starter-websocket")

    // Redis (시세 캐시 + Pub/Sub)
    implementation("org.springframework.boot:spring-boot-starter-data-redis")

    // Kafka Consumer (체결 이벤트 수신)
    implementation("org.springframework.kafka:spring-kafka")

    // Jackson
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")

    // Swagger
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0")

    // Lombok
    compileOnly("org.projectlombok:lombok")
    annotationProcessor("org.projectlombok:lombok")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.springframework.kafka:spring-kafka-test")
}

tasks.withType<Test> { useJUnitPlatform() }
""")

# ──────────────────────────────────────────────────────────────────
# 2. application.yml
# ──────────────────────────────────────────────────────────────────
write(os.path.join(RES, "application.yml"), """\
spring:
  application:
    name: market-data-service

  data:
    redis:
      host: ${SPRING_DATA_REDIS_HOST:localhost}
      port: ${SPRING_DATA_REDIS_PORT:6379}

  kafka:
    bootstrap-servers: ${SPRING_KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    consumer:
      group-id: market-data-group
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer

server:
  port: 8083

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

# Redis 키 설정
market:
  redis:
    ticker-prefix: "ticker:"           # ticker:{symbol} → 현재 시세 Hash
    ohlcv-prefix: "ohlcv:"             # ohlcv:{symbol}:{interval} → ZSet
    ticker-ttl-seconds: 300            # 5분 TTL
  websocket:
    topic-prefix: "/topic/ticker/"     # 클라이언트 구독 경로
  kafka:
    order-topic: order-events
    order-status-topic: order-status-events

logging:
  level:
    com.exchange.marketdata: DEBUG
    org.springframework.kafka: WARN
""")

# ──────────────────────────────────────────────────────────────────
# 3. Application 진입점
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "MarketDataServiceApplication.java"), """\
package com.exchange.marketdata;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Market Data Service — 실시간 시세/OHLCV 브로드캐스팅
 * Port: 8083
 * - STOMP WebSocket: /ws (클라이언트 ↔ 서버 양방향)
 * - Redis Pub/Sub: 멀티 인스턴스 간 시세 동기화
 * - Kafka Consumer: 체결 이벤트 → 시세 업데이트
 */
@SpringBootApplication
@EnableScheduling
public class MarketDataServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MarketDataServiceApplication.class, args);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 4. 도메인 DTO
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "ticker", "dto", "TickerDto.java"), """\
package com.exchange.marketdata.domain.ticker.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 현재 시세 스냅샷
 * WebSocket /topic/ticker/{symbol} 으로 브로드캐스트
 * Redis Hash ticker:{symbol} 에 저장
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class TickerDto {
    private String symbol;         // 종목 (예: AAPL, BTC-USD)
    private BigDecimal price;      // 현재가
    private BigDecimal open;       // 시가
    private BigDecimal high;       // 고가
    private BigDecimal low;        // 저가
    private BigDecimal prevClose;  // 전일 종가
    private BigDecimal change;     // 전일 대비 변동금액
    private BigDecimal changeRate; // 전일 대비 변동률(%)
    private Long volume;           // 거래량
    private BigDecimal turnover;   // 거래대금
    private LocalDateTime timestamp;
}
""")

write(os.path.join(SRC, "domain", "ohlcv", "dto", "OhlcvDto.java"), """\
package com.exchange.marketdata.domain.ohlcv.dto;

import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * OHLCV 캔들 데이터
 * Redis ZSet ohlcv:{symbol}:{interval} 에 score=timestamp 로 저장
 * interval: 1m, 5m, 15m, 1h, 1d
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OhlcvDto {
    private String symbol;
    private String interval;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Long volume;
    private LocalDateTime openTime;
    private LocalDateTime closeTime;
}
""")

write(os.path.join(SRC, "domain", "ticker", "dto", "MarketEventDto.java"), """\
package com.exchange.marketdata.domain.ticker.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.math.BigDecimal;

/**
 * Kafka에서 수신하는 체결 이벤트 페이로드
 * order-service의 Outbox에서 발행된 JSON 역직렬화 대상
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MarketEventDto {
    private Long orderId;
    private String productName;  // 종목명(심볼)
    private Integer quantity;
    private BigDecimal totalPrice;
    private String status;
    private String orderType;
}
""")

# ──────────────────────────────────────────────────────────────────
# 5. Redis 설정 (RedisTemplate + Pub/Sub ListenerContainer)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "config", "RedisConfig.java"), """\
package com.exchange.marketdata.config;

import com.exchange.marketdata.infrastructure.redis.MarketDataRedisSubscriber;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.listener.PatternTopic;
import org.springframework.data.redis.listener.RedisMessageListenerContainer;
import org.springframework.data.redis.listener.adapter.MessageListenerAdapter;
import org.springframework.data.redis.serializer.GenericJackson2JsonRedisSerializer;
import org.springframework.data.redis.serializer.StringRedisSerializer;

/**
 * Redis 설정
 * - RedisTemplate: 시세 Hash 저장용
 * - RedisMessageListenerContainer: Pub/Sub 구독 (멀티 인스턴스 동기화)
 */
@Configuration
public class RedisConfig {

    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(new GenericJackson2JsonRedisSerializer());
        template.setHashValueSerializer(new GenericJackson2JsonRedisSerializer());
        return template;
    }

    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        return mapper;
    }

    /**
     * Pub/Sub 구독 컨테이너
     * "market.ticker.*" 패턴으로 발행된 메시지를 MarketDataRedisSubscriber가 처리
     */
    @Bean
    public RedisMessageListenerContainer redisMessageListenerContainer(
            RedisConnectionFactory factory,
            MessageListenerAdapter listenerAdapter) {
        RedisMessageListenerContainer container = new RedisMessageListenerContainer();
        container.setConnectionFactory(factory);
        container.addMessageListener(listenerAdapter, new PatternTopic("market.ticker.*"));
        return container;
    }

    @Bean
    public MessageListenerAdapter messageListenerAdapter(MarketDataRedisSubscriber subscriber) {
        return new MessageListenerAdapter(subscriber, "onMessage");
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 6. WebSocket 설정 (STOMP)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "config", "WebSocketConfig.java"), """\
package com.exchange.marketdata.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.messaging.simp.config.MessageBrokerRegistry;
import org.springframework.web.socket.config.annotation.EnableWebSocketMessageBroker;
import org.springframework.web.socket.config.annotation.StompEndpointRegistry;
import org.springframework.web.socket.config.annotation.WebSocketMessageBrokerConfigurer;

/**
 * STOMP WebSocket 설정
 *
 * 클라이언트 연결:  ws://localhost:8083/ws
 * 구독 경로:        /topic/ticker/{symbol}  → 시세 수신
 *                   /topic/ohlcv/{symbol}    → 캔들 수신
 * 발행 경로:        /app/subscribe          → 구독 요청 (서버에서 처리)
 */
@Configuration
@EnableWebSocketMessageBroker
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        // 인메모리 브로커 — /topic 경로로 브로드캐스트
        registry.enableSimpleBroker("/topic");
        // 클라이언트 → 서버 메시지 prefix
        registry.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")
                .withSockJS(); // SockJS fallback
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 7. 시세 서비스
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "ticker", "service", "TickerService.java"), """\
package com.exchange.marketdata.domain.ticker.service;

import com.exchange.marketdata.domain.ticker.dto.TickerDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.time.LocalDateTime;
import java.util.Optional;

/**
 * 시세 업데이트 + WebSocket 브로드캐스트 + Redis Pub/Sub 발행
 *
 * 흐름:
 * 1. Kafka 체결 이벤트 수신 (OrderEventKafkaConsumer)
 * 2. TickerService.updatePrice() 호출
 * 3. Redis에 현재 시세 저장 (ticker:{symbol})
 * 4. Redis Pub/Sub 발행 (market.ticker.{symbol}) → 멀티 인스턴스 동기화
 * 5. WebSocket /topic/ticker/{symbol} 브로드캐스트
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class TickerService {

    private final RedisTemplate<String, Object> redisTemplate;
    private final StringRedisTemplate stringRedisTemplate;
    private final SimpMessagingTemplate messagingTemplate;
    private final ObjectMapper objectMapper;

    @Value("${market.redis.ticker-prefix:ticker:}")
    private String tickerPrefix;

    @Value("${market.redis.ticker-ttl-seconds:300}")
    private long ttlSeconds;

    @Value("${market.websocket.topic-prefix:/topic/ticker/}")
    private String topicPrefix;

    /**
     * 체결 가격 기반 시세 업데이트
     */
    public void updatePrice(String symbol, BigDecimal executionPrice, Long volume) {
        String key = tickerPrefix + symbol;

        // 기존 시세 조회
        TickerDto existing = getTickerFromRedis(key);
        BigDecimal prevClose = existing != null ? existing.getPrevClose() : executionPrice;
        BigDecimal open      = existing != null && existing.getOpen() != null
                               ? existing.getOpen() : executionPrice;
        BigDecimal high      = existing != null && existing.getHigh() != null
                               ? existing.getHigh().max(executionPrice) : executionPrice;
        BigDecimal low       = existing != null && existing.getLow() != null
                               ? existing.getLow().min(executionPrice) : executionPrice;
        Long totalVolume     = existing != null && existing.getVolume() != null
                               ? existing.getVolume() + volume : volume;

        BigDecimal change     = executionPrice.subtract(prevClose);
        BigDecimal changeRate = prevClose.compareTo(BigDecimal.ZERO) != 0
                ? change.divide(prevClose, 4, RoundingMode.HALF_UP).multiply(BigDecimal.valueOf(100))
                : BigDecimal.ZERO;

        TickerDto ticker = TickerDto.builder()
                .symbol(symbol)
                .price(executionPrice)
                .open(open)
                .high(high)
                .low(low)
                .prevClose(prevClose)
                .change(change)
                .changeRate(changeRate.setScale(2, RoundingMode.HALF_UP))
                .volume(totalVolume)
                .turnover(executionPrice.multiply(BigDecimal.valueOf(totalVolume)))
                .timestamp(LocalDateTime.now())
                .build();

        // Redis 저장 (TTL 5분)
        saveToRedis(key, ticker);

        // Redis Pub/Sub 발행 → 다른 인스턴스에도 브로드캐스트 트리거
        publishToRedis(symbol, ticker);

        // WebSocket 브로드캐스트 (현재 인스턴스)
        broadcastToWebSocket(symbol, ticker);

        log.debug("[시세 업데이트] symbol={}, price={}, change={}%",
                symbol, executionPrice, changeRate);
    }

    /**
     * Redis에서 현재 시세 조회
     */
    public Optional<TickerDto> getTicker(String symbol) {
        return Optional.ofNullable(getTickerFromRedis(tickerPrefix + symbol));
    }

    private void saveToRedis(String key, TickerDto ticker) {
        try {
            String json = objectMapper.writeValueAsString(ticker);
            stringRedisTemplate.opsForValue().set(key, json, Duration.ofSeconds(ttlSeconds));
        } catch (JsonProcessingException e) {
            log.error("[Redis 저장 실패] key={}, error={}", key, e.getMessage());
        }
    }

    private void publishToRedis(String symbol, TickerDto ticker) {
        try {
            String channel = "market.ticker." + symbol;
            stringRedisTemplate.convertAndSend(channel, objectMapper.writeValueAsString(ticker));
        } catch (JsonProcessingException e) {
            log.error("[Redis Pub/Sub 발행 실패] symbol={}", symbol);
        }
    }

    public void broadcastToWebSocket(String symbol, TickerDto ticker) {
        messagingTemplate.convertAndSend(topicPrefix + symbol, ticker);
    }

    private TickerDto getTickerFromRedis(String key) {
        try {
            String json = stringRedisTemplate.opsForValue().get(key);
            if (json == null) return null;
            return objectMapper.readValue(json, TickerDto.class);
        } catch (Exception e) {
            log.warn("[Redis 조회 실패] key={}", key);
            return null;
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 8. OHLCV 서비스
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "ohlcv", "service", "OhlcvService.java"), """\
package com.exchange.marketdata.domain.ohlcv.service;

import com.exchange.marketdata.domain.ohlcv.dto.OhlcvDto;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.data.redis.core.ZSetOperations;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * OHLCV (캔들) 데이터 관리
 * Redis ZSet: ohlcv:{symbol}:{interval}
 * - score = openTime 의 epoch second (시각 순 정렬)
 * - value = OhlcvDto JSON
 * - 각 인터벌별 최대 500개 보관 (LTRIM 방식 유사하게 ZREMRANGEBYRANK)
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OhlcvService {

    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    @Value("${market.redis.ohlcv-prefix:ohlcv:}")
    private String ohlcvPrefix;

    private static final int MAX_CANDLES = 500;

    /**
     * 체결 이벤트 발생 시 해당 인터벌 캔들 업데이트
     */
    public void update(String symbol, String interval,
                       BigDecimal price, Long volume, LocalDateTime time) {
        String key = ohlcvPrefix + symbol + ":" + interval;

        // 현재 진행 중인 캔들 조회 (ZSet 마지막 요소)
        Set<String> last = stringRedisTemplate.opsForZSet().range(key, -1, -1);
        OhlcvDto current = null;
        if (last != null && !last.isEmpty()) {
            current = deserialize(last.iterator().next());
        }

        LocalDateTime candle = truncateToInterval(time, interval);
        double score = candle.toEpochSecond(ZoneOffset.UTC);

        OhlcvDto updated;
        if (current != null && current.getOpenTime().equals(candle)) {
            // 기존 캔들 업데이트
            updated = OhlcvDto.builder()
                    .symbol(symbol)
                    .interval(interval)
                    .open(current.getOpen())
                    .high(current.getHigh().max(price))
                    .low(current.getLow().min(price))
                    .close(price)
                    .volume(current.getVolume() + volume)
                    .openTime(candle)
                    .closeTime(getCloseTime(candle, interval))
                    .build();
            // 기존 점수 제거 후 재삽입
            stringRedisTemplate.opsForZSet().removeRangeByScore(key, score, score);
        } else {
            // 새 캔들 시작
            updated = OhlcvDto.builder()
                    .symbol(symbol)
                    .interval(interval)
                    .open(price).high(price).low(price).close(price)
                    .volume(volume)
                    .openTime(candle)
                    .closeTime(getCloseTime(candle, interval))
                    .build();
        }

        try {
            stringRedisTemplate.opsForZSet().add(key, objectMapper.writeValueAsString(updated), score);
            // 최대 개수 초과 시 오래된 캔들 제거
            Long size = stringRedisTemplate.opsForZSet().zCard(key);
            if (size != null && size > MAX_CANDLES) {
                stringRedisTemplate.opsForZSet().removeRange(key, 0, size - MAX_CANDLES - 1);
            }
        } catch (JsonProcessingException e) {
            log.error("[OHLCV 저장 실패] symbol={}, interval={}", symbol, interval);
        }
    }

    /**
     * 최근 N개 캔들 조회
     */
    public List<OhlcvDto> getCandles(String symbol, String interval, int limit) {
        String key = ohlcvPrefix + symbol + ":" + interval;
        Set<String> raw = stringRedisTemplate.opsForZSet().reverseRange(key, 0, limit - 1);
        if (raw == null) return List.of();

        List<OhlcvDto> result = new ArrayList<>();
        for (String json : raw) {
            OhlcvDto dto = deserialize(json);
            if (dto != null) result.add(dto);
        }
        return result;
    }

    private LocalDateTime truncateToInterval(LocalDateTime time, String interval) {
        return switch (interval) {
            case "1m"  -> time.withSecond(0).withNano(0);
            case "5m"  -> time.withMinute((time.getMinute() / 5) * 5).withSecond(0).withNano(0);
            case "15m" -> time.withMinute((time.getMinute() / 15) * 15).withSecond(0).withNano(0);
            case "1h"  -> time.withMinute(0).withSecond(0).withNano(0);
            case "1d"  -> time.withHour(0).withMinute(0).withSecond(0).withNano(0);
            default    -> time.withSecond(0).withNano(0);
        };
    }

    private LocalDateTime getCloseTime(LocalDateTime open, String interval) {
        return switch (interval) {
            case "1m"  -> open.plusMinutes(1).minusNanos(1);
            case "5m"  -> open.plusMinutes(5).minusNanos(1);
            case "15m" -> open.plusMinutes(15).minusNanos(1);
            case "1h"  -> open.plusHours(1).minusNanos(1);
            case "1d"  -> open.plusDays(1).minusNanos(1);
            default    -> open.plusMinutes(1).minusNanos(1);
        };
    }

    private OhlcvDto deserialize(String json) {
        try {
            return objectMapper.readValue(json, OhlcvDto.class);
        } catch (Exception e) {
            return null;
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 9. Kafka Consumer (체결 이벤트 → 시세 업데이트)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "infrastructure", "kafka", "OrderEventKafkaConsumer.java"), """\
package com.exchange.marketdata.infrastructure.kafka;

import com.exchange.marketdata.domain.ohlcv.service.OhlcvService;
import com.exchange.marketdata.domain.ticker.dto.MarketEventDto;
import com.exchange.marketdata.domain.ticker.service.TickerService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

/**
 * Kafka Consumer — order-events 토픽에서 체결 이벤트 수신
 * COMPLETED 상태의 주문 → 시세 및 OHLCV 업데이트
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderEventKafkaConsumer {

    private final TickerService tickerService;
    private final OhlcvService ohlcvService;
    private final ObjectMapper objectMapper;

    private static final List<String> OHLCV_INTERVALS = List.of("1m", "5m", "15m", "1h", "1d");

    @KafkaListener(topics = "${market.kafka.order-topic:order-events}",
                   groupId = "market-data-group")
    public void consume(String message) {
        try {
            // Outbox payload는 Map 구조로 직렬화됨
            Map<?, ?> payload = objectMapper.readValue(message, Map.class);
            String status = (String) payload.get("status");

            // COMPLETED 주문만 시세 업데이트에 반영
            if (!"COMPLETED".equals(status)) return;

            String symbol     = (String) payload.get("productName");
            BigDecimal price  = new BigDecimal(payload.get("totalPrice").toString());
            Long quantity     = Long.valueOf(payload.get("quantity").toString());
            LocalDateTime now = LocalDateTime.now();

            // 티커 업데이트 + WebSocket 브로드캐스트
            tickerService.updatePrice(symbol, price, quantity);

            // 모든 인터벌 OHLCV 업데이트
            for (String interval : OHLCV_INTERVALS) {
                ohlcvService.update(symbol, interval, price, quantity, now);
            }

            log.info("[Market] 시세 업데이트 — symbol={}, price={}, qty={}", symbol, price, quantity);
        } catch (Exception e) {
            log.error("[Market] 이벤트 처리 실패: {}", e.getMessage());
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 10. Redis Pub/Sub 구독자 (멀티 인스턴스 동기화)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "infrastructure", "redis", "MarketDataRedisSubscriber.java"), """\
package com.exchange.marketdata.infrastructure.redis;

import com.exchange.marketdata.domain.ticker.dto.TickerDto;
import com.exchange.marketdata.domain.ticker.service.TickerService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.stereotype.Component;

/**
 * Redis Pub/Sub 구독자
 * 다른 인스턴스가 발행한 "market.ticker.*" 메시지를 수신
 * → WebSocket /topic/ticker/{symbol} 브로드캐스트
 *
 * 단일 인스턴스에서는 불필요하지만, 수평 확장 시 모든 인스턴스에 시세 동기화 보장
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class MarketDataRedisSubscriber implements MessageListener {

    private final TickerService tickerService;
    private final ObjectMapper objectMapper;

    @Override
    public void onMessage(Message message, byte[] pattern) {
        try {
            String body    = new String(message.getBody());
            String channel = new String(message.getChannel());
            // channel = "market.ticker.{symbol}"
            String symbol  = channel.substring(channel.lastIndexOf('.') + 1);

            TickerDto ticker = objectMapper.readValue(body, TickerDto.class);
            tickerService.broadcastToWebSocket(symbol, ticker);
            log.debug("[Redis Sub] 시세 수신 — symbol={}, price={}", symbol, ticker.getPrice());
        } catch (Exception e) {
            log.error("[Redis Sub] 메시지 처리 실패: {}", e.getMessage());
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 11. WebSocket Controller (구독 요청 처리)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "ticker", "controller", "MarketWebSocketController.java"), """\
package com.exchange.marketdata.domain.ticker.controller;

import com.exchange.marketdata.domain.ticker.dto.TickerDto;
import com.exchange.marketdata.domain.ticker.service.TickerService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;

import java.util.Optional;

/**
 * STOMP 메시지 핸들러
 * 클라이언트가 /app/subscribe/{symbol} 으로 구독 요청 시
 * 현재 시세를 즉시 /topic/ticker/{symbol} 로 전송
 */
@Slf4j
@Controller
@RequiredArgsConstructor
public class MarketWebSocketController {

    private final TickerService tickerService;

    @MessageMapping("/subscribe/{symbol}")
    @SendTo("/topic/ticker/{symbol}")
    public TickerDto subscribe(@DestinationVariable String symbol) {
        log.debug("[WS] 구독 요청 — symbol={}", symbol);
        return tickerService.getTicker(symbol)
                .orElse(TickerDto.builder().symbol(symbol).build());
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 12. REST Controller
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "ticker", "controller", "MarketDataRestController.java"), """\
package com.exchange.marketdata.domain.ticker.controller;

import com.exchange.marketdata.common.response.ApiResponse;
import com.exchange.marketdata.domain.ohlcv.dto.OhlcvDto;
import com.exchange.marketdata.domain.ohlcv.service.OhlcvService;
import com.exchange.marketdata.domain.ticker.dto.TickerDto;
import com.exchange.marketdata.domain.ticker.service.TickerService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Market Data API", description = "실시간 시세 / OHLCV 조회")
@RestController
@RequestMapping("/api/v1/market")
@RequiredArgsConstructor
public class MarketDataRestController {

    private final TickerService tickerService;
    private final OhlcvService ohlcvService;

    @Operation(summary = "현재 시세 조회")
    @GetMapping("/ticker/{symbol}")
    public ResponseEntity<ApiResponse<TickerDto>> getTicker(@PathVariable String symbol) {
        TickerDto ticker = tickerService.getTicker(symbol)
                .orElseThrow(() -> new IllegalArgumentException("시세 정보가 없습니다: " + symbol));
        return ResponseEntity.ok(ApiResponse.success(ticker));
    }

    @Operation(summary = "OHLCV 캔들 조회")
    @GetMapping("/ohlcv/{symbol}")
    public ResponseEntity<ApiResponse<List<OhlcvDto>>> getOhlcv(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval,
            @RequestParam(defaultValue = "100") int limit) {
        List<OhlcvDto> candles = ohlcvService.getCandles(symbol, interval,
                Math.min(limit, 500));
        return ResponseEntity.ok(ApiResponse.success(candles));
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 13. 공통 응답
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "common", "response", "ApiResponse.java"), """\
package com.exchange.marketdata.common.response;

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

    public static <T> ApiResponse<T> error(String message) {
        return new ApiResponse<>(false, message, null);
    }
}
""")

write(os.path.join(SRC, "common", "exception", "GlobalExceptionHandler.java"), """\
package com.exchange.marketdata.common.exception;

import com.exchange.marketdata.common.response.ApiResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

@Slf4j
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgument(IllegalArgumentException e) {
        return ResponseEntity.badRequest().body(ApiResponse.error(e.getMessage()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleGeneral(Exception e) {
        log.error("[서버 오류]", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.error("서버 내부 오류가 발생했습니다."));
    }
}
""")

print()
print("=== Phase 4 생성 완료 ===")
print("서비스: services/market-data-service")
print("핵심 파일:")
print("  - TickerService: 시세 업데이트 + Redis 저장 + WebSocket 브로드캐스트")
print("  - OhlcvService: Redis ZSet 기반 캔들 관리 (1m/5m/15m/1h/1d)")
print("  - OrderEventKafkaConsumer: 체결 이벤트 → 시세 업데이트")
print("  - MarketDataRedisSubscriber: Redis Pub/Sub 멀티 인스턴스 동기화")
print("  - WebSocketConfig: STOMP /ws 엔드포인트")
print("다음: ./gradlew.bat :services:market-data-service:compileJava")
