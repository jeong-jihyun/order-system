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
