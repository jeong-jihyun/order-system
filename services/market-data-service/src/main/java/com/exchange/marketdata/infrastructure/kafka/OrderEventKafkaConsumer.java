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
 * Kafka Consumer — order-status-events 토픽에서 체결 이벤트 수신
 * trading-engine이 매칭 완료 후 발행하는 ExecutionResult 이벤트 처리
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderEventKafkaConsumer {

    private final TickerService tickerService;
    private final OhlcvService ohlcvService;
    private final ObjectMapper objectMapper;

    private static final List<String> OHLCV_INTERVALS = List.of("1m", "5m", "15m", "1h", "1d");

    @KafkaListener(topics = "${market.kafka.order-topic:order-status-events}",
                   groupId = "market-data-group")
    public void consume(String message) {
        try {
            Map<?, ?> payload = objectMapper.readValue(message, Map.class);

            // order-status-events의 체결 이벤트 형식: symbol, executionPrice, executionQuantity
            String symbol = (String) payload.get("symbol");
            if (symbol == null) return;

            Object priceRaw = payload.get("executionPrice");
            Object qtyRaw   = payload.get("executionQuantity");
            if (priceRaw == null || qtyRaw == null) return;

            BigDecimal price    = new BigDecimal(priceRaw.toString());
            Long quantity       = new BigDecimal(qtyRaw.toString()).longValue();
            LocalDateTime now   = LocalDateTime.now();

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
