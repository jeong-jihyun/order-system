package com.exchange.order.kafka.consumer;

import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/**
 * Kafka Consumer — 다른 서비스에서 발행한 이벤트 수신
 * (Phase 3-5에서 account-service, trading-engine 이벤트 수신)
 */
@Slf4j
@Component
public class OrderEventConsumer {

    @KafkaListener(topics = "order-events", groupId = "order-service-group")
    public void consume(String message) {
        log.info("[Kafka Consumer] 이벤트 수신: {}", message);
        // Phase 3 이후 구체적 처리 로직 추가 예정
    }
}
