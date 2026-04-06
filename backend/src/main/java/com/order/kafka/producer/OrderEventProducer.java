package com.order.kafka.producer;

import com.order.config.KafkaConfig;
import com.order.kafka.event.OrderEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Component;

/**
 * [Week 2 - Kafka Producer]
 * KafkaTemplate으로 order-events 토픽에 메시지 발행.
 * sendOrderEvent() 호출 후 비동기로 성공/실패 콜백 처리.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderEventProducer {

    private final KafkaTemplate<String, OrderEvent> kafkaTemplate;

    public void sendOrderEvent(OrderEvent event) {
        kafkaTemplate.send(KafkaConfig.ORDER_TOPIC, String.valueOf(event.getOrderId()), event)
                .whenComplete((result, ex) -> {
                    if (ex == null) {
                        log.info("[Kafka] 이벤트 발행 성공 — orderId={}, partition={}, offset={}",
                                event.getOrderId(),
                                result.getRecordMetadata().partition(),
                                result.getRecordMetadata().offset());
                    } else {
                        log.error("[Kafka] 이벤트 발행 실패 — orderId={}", event.getOrderId(), ex);
                    }
                });
    }
}
