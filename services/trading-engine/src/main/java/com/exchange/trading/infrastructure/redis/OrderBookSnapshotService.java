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
