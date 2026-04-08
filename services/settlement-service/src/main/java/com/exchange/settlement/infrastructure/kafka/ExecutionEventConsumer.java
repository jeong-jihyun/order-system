package com.exchange.settlement.infrastructure.kafka;

import com.exchange.settlement.domain.settlement.service.SettlementService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.Map;

/**
 * Kafka Consumer — order-status-events (체결 결과) 수신
 * buyFilled=true && sellFilled=true → 완전 체결로 간주하여 정산 처리
 * 부분 체결은 누적 관리 필요 (현재 간략 구현)
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ExecutionEventConsumer {

    private final SettlementService settlementService;
    private final ObjectMapper objectMapper;

    @KafkaListener(topics = "${settlement.kafka.execution-topic:order-status-events}",
                   groupId = "settlement-service-group")
    public void consume(String message) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> payload = objectMapper.readValue(message, Map.class);

            Long buyOrderId  = Long.valueOf(payload.get("buyOrderId").toString());
            Long sellOrderId = Long.valueOf(payload.get("sellOrderId").toString());
            String symbol    = (String) payload.get("symbol");
            BigDecimal price = new BigDecimal(payload.get("executionPrice").toString());
            BigDecimal qty   = new BigDecimal(payload.get("executionQuantity").toString());
            LocalDateTime executedAt = LocalDateTime.parse(payload.get("executedAt").toString());

            // username은 별도 조회 필요 — 현재는 orderId를 임시 사용 (account-service 연동 예정)
            String buyerUsername  = "user-" + buyOrderId;
            String sellerUsername = "user-" + sellOrderId;

            settlementService.processExecution(
                    buyOrderId, sellOrderId, symbol, price, qty, executedAt,
                    buyerUsername, sellerUsername);

        } catch (Exception e) {
            log.error("[ExecutionEventConsumer] 처리 실패: {}", e.getMessage(), e);
        }
    }
}
