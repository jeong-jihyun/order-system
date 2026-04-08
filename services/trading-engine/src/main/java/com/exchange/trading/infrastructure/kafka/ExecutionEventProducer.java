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
                "sellFilled",       result.isSellFilled(),
                "buyerUsername",    result.getBuyerUsername() != null ? result.getBuyerUsername() : "",
                "sellerUsername",   result.getSellerUsername() != null ? result.getSellerUsername() : ""
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
