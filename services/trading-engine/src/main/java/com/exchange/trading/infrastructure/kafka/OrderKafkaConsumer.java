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
            @SuppressWarnings("unchecked")
            Map<String, Object> payload = objectMapper.readValue(message, Map.class);
            String status = (String) payload.get("status");

            // PENDING 주문만 매칭 처리
            if (!"PENDING".equals(status)) return;

            Long orderId     = Long.valueOf(payload.get("orderId").toString());
            String symbol    = (String) payload.get("productName");
            BigDecimal price = new BigDecimal(payload.get("totalPrice").toString());
            BigDecimal qty   = new BigDecimal(payload.get("quantity").toString());

            // order-service가 발행한 side 필드 사용 (BUY | SELL), 없으면 BUY 기본값
            String side = payload.getOrDefault("side", "BUY").toString().toUpperCase();

            executionService.processOrder(orderId, symbol, side, price, qty);

        } catch (Exception e) {
            log.error("[TradingEngine] 주문 처리 실패: {}", e.getMessage(), e);
        }
    }
}
