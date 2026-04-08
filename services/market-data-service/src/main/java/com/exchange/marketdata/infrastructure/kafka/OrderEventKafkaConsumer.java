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
