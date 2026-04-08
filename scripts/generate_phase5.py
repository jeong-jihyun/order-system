#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 5: trading-engine — 주문 매칭 엔진
- Order Book: 매수/매도 호가창 (ConcurrentSkipListMap — Price-Time Priority)
- MatchingEngine: 가격 우선 → 시간 우선 체결 알고리즘
- Redis: 호가창 스냅샷 저장 (10레벨)
- Kafka Consumer: order-events 수신 → 매칭 시도
- Kafka Producer: 체결 이벤트 발행 (order-status-events)
- Port: 8084
"""
import os

ROOT = r"d:\order-system"
TE   = os.path.join(ROOT, "services", "trading-engine")
SRC  = os.path.join(TE, "src", "main", "java", "com", "exchange", "trading")
RES  = os.path.join(TE, "src", "main", "resources")

def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK  {os.path.relpath(path, ROOT)}")

# ──────────────────────────────────────────────────────────────────
# 1. build.gradle.kts
# ──────────────────────────────────────────────────────────────────
write(os.path.join(TE, "build.gradle.kts"), """\
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
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.boot:spring-boot-starter-validation")
    implementation("org.springframework.boot:spring-boot-starter-actuator")
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.kafka:spring-kafka")
    implementation("com.fasterxml.jackson.core:jackson-databind")
    implementation("com.fasterxml.jackson.datatype:jackson-datatype-jsr310")
    implementation("org.springdoc:springdoc-openapi-starter-webmvc-ui:2.3.0")
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
    name: trading-engine

  data:
    redis:
      host: ${SPRING_DATA_REDIS_HOST:localhost}
      port: ${SPRING_DATA_REDIS_PORT:6379}

  kafka:
    bootstrap-servers: ${SPRING_KAFKA_BOOTSTRAP_SERVERS:localhost:9092}
    consumer:
      group-id: trading-engine-group
      auto-offset-reset: earliest
      key-deserializer: org.apache.kafka.common.serialization.StringDeserializer
      value-deserializer: org.apache.kafka.common.serialization.StringDeserializer
    producer:
      key-serializer: org.apache.kafka.common.serialization.StringSerializer
      value-serializer: org.apache.kafka.common.serialization.StringSerializer
      acks: all
      retries: 3
      properties:
        enable.idempotence: true

server:
  port: 8084

management:
  endpoints:
    web:
      exposure:
        include: health,info,metrics

trading:
  kafka:
    order-topic: order-events
    execution-topic: order-status-events
  orderbook:
    depth: 10          # 호가창 표시 레벨 수
    redis-prefix: "orderbook:"
    snapshot-ttl: 60   # 호가창 스냅샷 TTL (초)

logging:
  level:
    com.exchange.trading: DEBUG
    org.springframework.kafka: WARN
""")

# ──────────────────────────────────────────────────────────────────
# 3. Application 진입점
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "TradingEngineApplication.java"), """\
package com.exchange.trading;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Trading Engine — Price-Time Priority 주문 매칭 엔진
 * Port: 8084
 * - Order Book: ConcurrentSkipListMap 기반 (자동 가격 정렬)
 * - Matching: 가격 우선 → 시간 우선 (FIFO per price level)
 * - Kafka Consumer: 신규 주문 수신
 * - Kafka Producer: 체결 결과 발행
 */
@SpringBootApplication
@EnableAsync
public class TradingEngineApplication {
    public static void main(String[] args) {
        SpringApplication.run(TradingEngineApplication.class, args);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 4. 핵심 도메인 — Order (매칭용)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "orderbook", "entity", "OrderSide.java"), """\
package com.exchange.trading.domain.orderbook.entity;

public enum OrderSide {
    BUY,   // 매수
    SELL   // 매도
}
""")

write(os.path.join(SRC, "domain", "orderbook", "entity", "OrderBookEntry.java"), """\
package com.exchange.trading.domain.orderbook.entity;

import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 호가창에 보관되는 주문 항목
 * - price: 지정가 (MARKET 주문은 null)
 * - sequence: 동일 가격 내 시간 우선을 위한 단조 증가 시퀀스
 */
@Getter
@Builder
public class OrderBookEntry implements Comparable<OrderBookEntry> {

    private static final AtomicLong SEQUENCE = new AtomicLong(0);

    private final Long orderId;
    private final String symbol;
    private final OrderSide side;
    private final BigDecimal price;     // null이면 MARKET 주문
    private final BigDecimal originalQuantity;
    private volatile BigDecimal remainingQuantity;
    private final LocalDateTime createdAt;
    private final long sequence;        // 시간 우선 정렬용

    public static OrderBookEntry create(Long orderId, String symbol, OrderSide side,
                                        BigDecimal price, BigDecimal quantity) {
        return OrderBookEntry.builder()
                .orderId(orderId)
                .symbol(symbol)
                .side(side)
                .price(price)
                .originalQuantity(quantity)
                .remainingQuantity(quantity)
                .createdAt(LocalDateTime.now())
                .sequence(SEQUENCE.incrementAndGet())
                .build();
    }

    public void fill(BigDecimal filledQuantity) {
        this.remainingQuantity = this.remainingQuantity.subtract(filledQuantity);
    }

    public boolean isFilled() {
        return remainingQuantity.compareTo(BigDecimal.ZERO) <= 0;
    }

    /**
     * 동일 가격 내 시간 우선 (sequence 오름차순)
     */
    @Override
    public int compareTo(OrderBookEntry other) {
        return Long.compare(this.sequence, other.sequence);
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 5. Order Book (ConcurrentSkipListMap 기반)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "orderbook", "service", "OrderBook.java"), """\
package com.exchange.trading.domain.orderbook.service;

import com.exchange.trading.domain.orderbook.entity.OrderBookEntry;
import com.exchange.trading.domain.orderbook.entity.OrderSide;
import lombok.extern.slf4j.Slf4j;

import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.ConcurrentSkipListMap;

/**
 * 종목별 호가창 (Order Book)
 *
 * 자료구조:
 * - 매수 (BUY):  ConcurrentSkipListMap (내림차순) — 높은 가격 우선
 * - 매도 (SELL): ConcurrentSkipListMap (오름차순) — 낮은 가격 우선
 * - 각 가격 레벨: TreeSet<OrderBookEntry> (sequence 오름차순 — 시간 우선 FIFO)
 *
 * Thread-Safety: ConcurrentSkipListMap + synchronized per price level
 */
@Slf4j
public class OrderBook {

    private final String symbol;

    // 매수 호가: 높은 가격 → 낮은 가격 (내림차순)
    private final ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> bids =
            new ConcurrentSkipListMap<>(Comparator.reverseOrder());

    // 매도 호가: 낮은 가격 → 높은 가격 (오름차순)
    private final ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> asks =
            new ConcurrentSkipListMap<>();

    public OrderBook(String symbol) {
        this.symbol = symbol;
    }

    /**
     * 주문 추가
     */
    public void addOrder(OrderBookEntry entry) {
        ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> book =
                entry.getSide() == OrderSide.BUY ? bids : asks;
        book.computeIfAbsent(entry.getPrice(), k -> new TreeSet<>())
            .add(entry);
        log.debug("[OrderBook] 주문 등록 — symbol={}, side={}, price={}, qty={}",
                symbol, entry.getSide(), entry.getPrice(), entry.getRemainingQuantity());
    }

    /**
     * 주문 취소
     */
    public boolean cancelOrder(Long orderId, OrderSide side, BigDecimal price) {
        ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> book =
                side == OrderSide.BUY ? bids : asks;
        TreeSet<OrderBookEntry> level = book.get(price);
        if (level == null) return false;
        boolean removed = level.removeIf(e -> e.getOrderId().equals(orderId));
        if (level.isEmpty()) book.remove(price);
        return removed;
    }

    /**
     * 최우선 매수 호가 (Best Bid)
     */
    public Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestBid() {
        return bids.isEmpty() ? Optional.empty()
                              : Optional.of(bids.firstEntry());
    }

    /**
     * 최우선 매도 호가 (Best Ask)
     */
    public Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestAsk() {
        return asks.isEmpty() ? Optional.empty()
                              : Optional.of(asks.firstEntry());
    }

    /**
     * 가격 레벨별 매수/매도 호가 스냅샷 (상위 depth 개)
     */
    public OrderBookSnapshot getSnapshot(int depth) {
        List<PriceLevel> bidLevels = new ArrayList<>();
        List<PriceLevel> askLevels = new ArrayList<>();

        int count = 0;
        for (Map.Entry<BigDecimal, TreeSet<OrderBookEntry>> e : bids.entrySet()) {
            if (count++ >= depth) break;
            BigDecimal total = e.getValue().stream()
                    .map(OrderBookEntry::getRemainingQuantity)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            bidLevels.add(new PriceLevel(e.getKey(), total, e.getValue().size()));
        }

        count = 0;
        for (Map.Entry<BigDecimal, TreeSet<OrderBookEntry>> e : asks.entrySet()) {
            if (count++ >= depth) break;
            BigDecimal total = e.getValue().stream()
                    .map(OrderBookEntry::getRemainingQuantity)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            askLevels.add(new PriceLevel(e.getKey(), total, e.getValue().size()));
        }

        return new OrderBookSnapshot(symbol, bidLevels, askLevels);
    }

    public void removePriceLevel(OrderSide side, BigDecimal price) {
        if (side == OrderSide.BUY) bids.remove(price);
        else asks.remove(price);
    }

    public ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> getBids() { return bids; }
    public ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> getAsks() { return asks; }
    public String getSymbol() { return symbol; }

    // ── 내부 DTO ──────────────────────────────────────────────────
    public record PriceLevel(BigDecimal price, BigDecimal quantity, int orderCount) {}

    public record OrderBookSnapshot(String symbol,
                                    List<PriceLevel> bids,
                                    List<PriceLevel> asks) {}
}
""")

# ──────────────────────────────────────────────────────────────────
# 6. 매칭 결과 DTO
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "matching", "dto", "ExecutionResult.java"), """\
package com.exchange.trading.domain.matching.dto;

import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 단일 체결 결과
 * - buyOrderId/sellOrderId: 매수/매도 주문 ID
 * - executionPrice: 체결가 (매도 호가 기준)
 * - executionQuantity: 체결 수량
 */
@Getter
@Builder
public class ExecutionResult {
    private final Long buyOrderId;
    private final Long sellOrderId;
    private final String symbol;
    private final BigDecimal executionPrice;
    private final BigDecimal executionQuantity;
    private final LocalDateTime executedAt;
    private final boolean buyFilled;   // 매수 주문 완전 체결 여부
    private final boolean sellFilled;  // 매도 주문 완전 체결 여부
}
""")

# ──────────────────────────────────────────────────────────────────
# 7. 핵심 — 매칭 엔진
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "matching", "service", "MatchingEngine.java"), """\
package com.exchange.trading.domain.matching.service;

import com.exchange.trading.domain.matching.dto.ExecutionResult;
import com.exchange.trading.domain.orderbook.entity.OrderBookEntry;
import com.exchange.trading.domain.orderbook.entity.OrderSide;
import com.exchange.trading.domain.orderbook.service.OrderBook;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

/**
 * Price-Time Priority 매칭 엔진
 *
 * 매칭 알고리즘:
 * 1. 신규 BUY 주문 → bestAsk와 비교: BUY.price >= ASK.price → 체결
 * 2. 신규 SELL 주문 → bestBid와 비교: SELL.price <= BID.price → 체결
 * 3. 부분 체결 지원: 수량이 남으면 호가창에 잔량 유지
 * 4. MARKET 주문: 가격 조건 없이 반대편 최우선 호가와 즉시 체결
 *
 * Thread-Safety: 종목별 OrderBook 단위로 synchronized
 */
@Slf4j
@Component
public class MatchingEngine {

    /**
     * 신규 주문 매칭 시도
     * @return 체결 결과 목록 (복수 체결 가능 - 여러 가격 레벨에 걸친 체결)
     */
    public List<ExecutionResult> match(OrderBook orderBook, OrderBookEntry newOrder) {
        List<ExecutionResult> executions = new ArrayList<>();

        synchronized (orderBook) {
            if (newOrder.getSide() == OrderSide.BUY) {
                matchBuyOrder(orderBook, newOrder, executions);
            } else {
                matchSellOrder(orderBook, newOrder, executions);
            }

            // 미체결 잔량이 있으면 호가창에 등록 (지정가 주문만)
            if (!newOrder.isFilled() && newOrder.getPrice() != null) {
                orderBook.addOrder(newOrder);
            }
        }

        return executions;
    }

    private void matchBuyOrder(OrderBook book, OrderBookEntry buyOrder,
                                List<ExecutionResult> executions) {
        while (!buyOrder.isFilled()) {
            Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestAskOpt = book.bestAsk();
            if (bestAskOpt.isEmpty()) break;

            BigDecimal askPrice = bestAskOpt.get().getKey();
            // MARKET 주문이거나 BUY 지정가 >= ASK 가격이면 체결 가능
            boolean canMatch = buyOrder.getPrice() == null
                    || buyOrder.getPrice().compareTo(askPrice) >= 0;
            if (!canMatch) break;

            TreeSet<OrderBookEntry> askLevel = bestAskOpt.get().getValue();
            Iterator<OrderBookEntry> it = askLevel.iterator();
            if (!it.hasNext()) { book.removePriceLevel(OrderSide.SELL, askPrice); break; }

            OrderBookEntry sellOrder = it.next();
            BigDecimal fillQty = buyOrder.getRemainingQuantity()
                    .min(sellOrder.getRemainingQuantity());

            buyOrder.fill(fillQty);
            sellOrder.fill(fillQty);

            executions.add(ExecutionResult.builder()
                    .buyOrderId(buyOrder.getOrderId())
                    .sellOrderId(sellOrder.getOrderId())
                    .symbol(buyOrder.getSymbol())
                    .executionPrice(askPrice)          // 체결가 = 매도 호가 기준
                    .executionQuantity(fillQty)
                    .executedAt(LocalDateTime.now())
                    .buyFilled(buyOrder.isFilled())
                    .sellFilled(sellOrder.isFilled())
                    .build());

            log.info("[체결] symbol={}, price={}, qty={}, buyId={}, sellId={}",
                    buyOrder.getSymbol(), askPrice, fillQty,
                    buyOrder.getOrderId(), sellOrder.getOrderId());

            if (sellOrder.isFilled()) {
                it.remove();
                if (askLevel.isEmpty()) book.removePriceLevel(OrderSide.SELL, askPrice);
            }
        }
    }

    private void matchSellOrder(OrderBook book, OrderBookEntry sellOrder,
                                 List<ExecutionResult> executions) {
        while (!sellOrder.isFilled()) {
            Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestBidOpt = book.bestBid();
            if (bestBidOpt.isEmpty()) break;

            BigDecimal bidPrice = bestBidOpt.get().getKey();
            // MARKET 주문이거나 SELL 지정가 <= BID 가격이면 체결 가능
            boolean canMatch = sellOrder.getPrice() == null
                    || sellOrder.getPrice().compareTo(bidPrice) <= 0;
            if (!canMatch) break;

            TreeSet<OrderBookEntry> bidLevel = bestBidOpt.get().getValue();
            Iterator<OrderBookEntry> it = bidLevel.iterator();
            if (!it.hasNext()) { book.removePriceLevel(OrderSide.BUY, bidPrice); break; }

            OrderBookEntry buyOrder = it.next();
            BigDecimal fillQty = sellOrder.getRemainingQuantity()
                    .min(buyOrder.getRemainingQuantity());

            sellOrder.fill(fillQty);
            buyOrder.fill(fillQty);

            executions.add(ExecutionResult.builder()
                    .buyOrderId(buyOrder.getOrderId())
                    .sellOrderId(sellOrder.getOrderId())
                    .symbol(sellOrder.getSymbol())
                    .executionPrice(bidPrice)          // 체결가 = 매수 호가 기준
                    .executionQuantity(fillQty)
                    .executedAt(LocalDateTime.now())
                    .buyFilled(buyOrder.isFilled())
                    .sellFilled(sellOrder.isFilled())
                    .build());

            log.info("[체결] symbol={}, price={}, qty={}, buyId={}, sellId={}",
                    sellOrder.getSymbol(), bidPrice, fillQty,
                    buyOrder.getOrderId(), sellOrder.getOrderId());

            if (buyOrder.isFilled()) {
                it.remove();
                if (bidLevel.isEmpty()) book.removePriceLevel(OrderSide.BUY, bidPrice);
            }
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 8. OrderBook 레지스트리 (종목별 OrderBook 관리)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "orderbook", "service", "OrderBookRegistry.java"), """\
package com.exchange.trading.domain.orderbook.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;

/**
 * 종목별 OrderBook 인스턴스 관리
 * ConcurrentHashMap: 종목 추가/조회 Thread-Safe
 */
@Slf4j
@Component
public class OrderBookRegistry {

    private final ConcurrentHashMap<String, OrderBook> orderBooks = new ConcurrentHashMap<>();

    public OrderBook getOrCreate(String symbol) {
        return orderBooks.computeIfAbsent(symbol, s -> {
            log.info("[OrderBook] 신규 종목 호가창 생성 — symbol={}", s);
            return new OrderBook(s);
        });
    }

    public OrderBook get(String symbol) {
        OrderBook ob = orderBooks.get(symbol);
        if (ob == null) throw new IllegalArgumentException("호가창이 없습니다: " + symbol);
        return ob;
    }

    public boolean exists(String symbol) { return orderBooks.containsKey(symbol); }
}
""")

# ──────────────────────────────────────────────────────────────────
# 9. 매칭 결과 처리 서비스
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "matching", "service", "ExecutionService.java"), """\
package com.exchange.trading.domain.matching.service;

import com.exchange.trading.domain.matching.dto.ExecutionResult;
import com.exchange.trading.domain.orderbook.entity.OrderBookEntry;
import com.exchange.trading.domain.orderbook.entity.OrderSide;
import com.exchange.trading.domain.orderbook.service.OrderBook;
import com.exchange.trading.domain.orderbook.service.OrderBookRegistry;
import com.exchange.trading.infrastructure.kafka.ExecutionEventProducer;
import com.exchange.trading.infrastructure.redis.OrderBookSnapshotService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

/**
 * 주문 접수 → 매칭 → 체결 이벤트 발행 → 호가창 스냅샷 저장
 * Kafka Consumer에서 호출
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ExecutionService {

    private final OrderBookRegistry registry;
    private final MatchingEngine matchingEngine;
    private final ExecutionEventProducer executionProducer;
    private final OrderBookSnapshotService snapshotService;

    public void processOrder(Long orderId, String symbol, String side,
                             BigDecimal price, BigDecimal quantity) {
        OrderSide orderSide = OrderSide.valueOf(side.toUpperCase());
        OrderBook orderBook = registry.getOrCreate(symbol);

        // MARKET 주문: price = null
        BigDecimal orderPrice = "MARKET".equalsIgnoreCase(side) ? null : price;

        OrderBookEntry entry = OrderBookEntry.create(orderId, symbol, orderSide,
                                                      orderPrice, quantity);

        // 매칭 실행
        List<ExecutionResult> executions = matchingEngine.match(orderBook, entry);

        // 체결 결과 Kafka 발행
        for (ExecutionResult exec : executions) {
            executionProducer.publishExecution(exec);
        }

        // 호가창 스냅샷 Redis 저장
        snapshotService.saveSnapshot(orderBook);

        if (!executions.isEmpty()) {
            log.info("[ExecutionService] {}건 체결 처리 완료 — symbol={}", executions.size(), symbol);
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 10. Kafka Consumer (신규 주문 수신)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "infrastructure", "kafka", "OrderKafkaConsumer.java"), """\
package com.exchange.trading.infrastructure.kafka;

import com.exchange.trading.domain.matching.service.ExecutionService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.Map;

/**
 * Kafka Consumer — order-events 수신
 * PENDING 상태의 신규 주문을 매칭 엔진으로 라우팅
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderKafkaConsumer {

    private final ExecutionService executionService;
    private final ObjectMapper objectMapper;

    @KafkaListener(topics = "${trading.kafka.order-topic:order-events}",
                   groupId = "trading-engine-group")
    public void consume(String message) {
        try {
            Map<?, ?> payload = objectMapper.readValue(message, Map.class);
            String status = (String) payload.get("status");

            // PENDING 주문만 매칭 처리
            if (!"PENDING".equals(status)) return;

            Long orderId      = Long.valueOf(payload.get("orderId").toString());
            String symbol     = (String) payload.get("productName");
            String orderType  = payload.getOrDefault("orderType", "LIMIT").toString();
            BigDecimal price  = new BigDecimal(payload.get("totalPrice").toString());
            BigDecimal qty    = new BigDecimal(payload.get("quantity").toString());

            // 주문 방향: 단순화를 위해 quantity > 0 이면 BUY, 추후 side 필드 추가 예정
            String side = "BUY"; // TODO: order-service에서 side 필드 포함해 발행

            executionService.processOrder(orderId, symbol, side, price, qty);

        } catch (Exception e) {
            log.error("[TradingEngine] 주문 처리 실패: {}", e.getMessage(), e);
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 11. Kafka Producer (체결 이벤트 발행)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "infrastructure", "kafka", "ExecutionEventProducer.java"), """\
package com.exchange.trading.infrastructure.kafka;

import com.exchange.trading.domain.matching.dto.ExecutionResult;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 체결 결과를 order-status-events 토픽으로 발행
 * order-service의 Outbox Relay가 수신하여 주문 상태를 COMPLETED로 업데이트
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ExecutionEventProducer {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Value("${trading.kafka.execution-topic:order-status-events}")
    private String executionTopic;

    public void publishExecution(ExecutionResult result) {
        try {
            Map<String, Object> payload = Map.of(
                "buyOrderId",       result.getBuyOrderId(),
                "sellOrderId",      result.getSellOrderId(),
                "symbol",           result.getSymbol(),
                "executionPrice",   result.getExecutionPrice(),
                "executionQuantity",result.getExecutionQuantity(),
                "executedAt",       result.getExecutedAt().toString(),
                "buyFilled",        result.isBuyFilled(),
                "sellFilled",       result.isSellFilled()
            );
            String json = objectMapper.writeValueAsString(payload);
            kafkaTemplate.send(executionTopic,
                               result.getBuyOrderId().toString(), json);
            log.info("[ExecutionProducer] 체결 이벤트 발행 — buyId={}, sellId={}, price={}",
                    result.getBuyOrderId(), result.getSellOrderId(), result.getExecutionPrice());
        } catch (JsonProcessingException e) {
            log.error("[ExecutionProducer] 직렬화 실패: {}", e.getMessage());
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 12. Redis 호가창 스냅샷
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "infrastructure", "redis", "OrderBookSnapshotService.java"), """\
package com.exchange.trading.infrastructure.redis;

import com.exchange.trading.domain.orderbook.service.OrderBook;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

import java.time.Duration;

/**
 * 호가창 스냅샷을 Redis에 저장
 * market-data-service / REST API에서 조회 가능
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OrderBookSnapshotService {

    private final StringRedisTemplate stringRedisTemplate;
    private final ObjectMapper objectMapper;

    @Value("${trading.orderbook.redis-prefix:orderbook:}")
    private String redisPrefix;

    @Value("${trading.orderbook.snapshot-ttl:60}")
    private long ttlSeconds;

    @Value("${trading.orderbook.depth:10}")
    private int depth;

    public void saveSnapshot(OrderBook orderBook) {
        try {
            OrderBook.OrderBookSnapshot snapshot = orderBook.getSnapshot(depth);
            String key  = redisPrefix + orderBook.getSymbol();
            String json = objectMapper.writeValueAsString(snapshot);
            stringRedisTemplate.opsForValue().set(key, json, Duration.ofSeconds(ttlSeconds));
        } catch (JsonProcessingException e) {
            log.error("[Snapshot] 저장 실패 — symbol={}", orderBook.getSymbol());
        }
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 13. Redis Config
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "config", "RedisConfig.java"), """\
package com.exchange.trading.config;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.datatype.jsr310.JavaTimeModule;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.data.redis.connection.RedisConnectionFactory;
import org.springframework.data.redis.core.StringRedisTemplate;

@Configuration
public class RedisConfig {

    @Bean
    public StringRedisTemplate stringRedisTemplate(RedisConnectionFactory factory) {
        return new StringRedisTemplate(factory);
    }

    @Bean
    public ObjectMapper objectMapper() {
        ObjectMapper mapper = new ObjectMapper();
        mapper.registerModule(new JavaTimeModule());
        return mapper;
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 14. REST Controller (호가창 조회)
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "domain", "orderbook", "controller", "OrderBookController.java"), """\
package com.exchange.trading.domain.orderbook.controller;

import com.exchange.trading.common.response.ApiResponse;
import com.exchange.trading.domain.orderbook.service.OrderBook;
import com.exchange.trading.domain.orderbook.service.OrderBookRegistry;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Tag(name = "Order Book API", description = "호가창 조회")
@RestController
@RequestMapping("/api/v1/orderbook")
@RequiredArgsConstructor
public class OrderBookController {

    private final OrderBookRegistry registry;

    @Operation(summary = "호가창 스냅샷 조회")
    @GetMapping("/{symbol}")
    public ResponseEntity<ApiResponse<OrderBook.OrderBookSnapshot>> getSnapshot(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "10") int depth) {
        OrderBook book = registry.getOrCreate(symbol);
        return ResponseEntity.ok(ApiResponse.success(book.getSnapshot(depth)));
    }
}
""")

# ──────────────────────────────────────────────────────────────────
# 15. 공통 응답/예외
# ──────────────────────────────────────────────────────────────────
write(os.path.join(SRC, "common", "response", "ApiResponse.java"), """\
package com.exchange.trading.common.response;

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
package com.exchange.trading.common.exception;

import com.exchange.trading.common.response.ApiResponse;
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
print("=== Phase 5 생성 완료 ===")
print("핵심 클래스:")
print("  - OrderBook: ConcurrentSkipListMap (매수 내림차순, 매도 오름차순)")
print("  - MatchingEngine: Price-Time Priority 알고리즘")
print("  - ExecutionService: 주문 접수 → 매칭 → 이벤트 발행")
print("  - OrderKafkaConsumer: order-events 수신 → PENDING 주문 처리")
print("  - ExecutionEventProducer: 체결 결과 order-status-events 발행")
print("  - OrderBookSnapshotService: Redis 호가창 스냅샷 저장")
print("다음: ./gradlew.bat :services:trading-engine:compileJava")
