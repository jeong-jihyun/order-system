package com.exchange.settlement.infrastructure.kafka;

import com.exchange.settlement.domain.settlement.entity.SettlementRecord;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

import java.util.Map;

/**
 * 정산 완료 이벤트 발행
 * account-service가 수신하여 실제 잔고 반영 처리
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SettlementEventProducer {

    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Value("${settlement.kafka.settlement-topic:settlement-events}")
    private String settlementTopic;

    public void publishSettlementComplete(SettlementRecord record) {
        try {
            Map<String, Object> payload = Map.of(
                "settlementId",  record.getId(),
                "orderId",       record.getOrderId(),
                "username",      record.getUsername(),
                "symbol",        record.getSymbol(),
                "side",          record.getSide(),
                "netAmount",     record.getNetAmount(),
                "settlementDate",record.getSettlementDate().toString()
            );
            String json = objectMapper.writeValueAsString(payload);
            kafkaTemplate.send(settlementTopic, record.getUsername(), json);
            log.info("[SettlementProducer] 정산 이벤트 발행 — id={}, username={}, netAmount={}",
                    record.getId(), record.getUsername(), record.getNetAmount());
        } catch (JsonProcessingException e) {
            log.error("[SettlementProducer] 직렬화 실패: {}", e.getMessage());
            throw new RuntimeException("정산 이벤트 발행 실패", e);
        }
    }
}
