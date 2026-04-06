package com.order.kafka.consumer;

import com.order.config.KafkaConfig;
import com.order.kafka.event.OrderEvent;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.messaging.simp.SimpMessagingTemplate;
import org.springframework.stereotype.Component;

/**
 * [Week 2 - Kafka Consumer]
 * order-events 토픽을 구독하여 이벤트를 처리.
 *
 * [Week 4 - WebSocket 연동]
 * SimpMessagingTemplate으로 /topic/orders 채널에 실시간 브로드캐스트.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderEventConsumer {

    private final SimpMessagingTemplate messagingTemplate;

    @KafkaListener(topics = KafkaConfig.ORDER_TOPIC, groupId = "order-group")
    public void consumeOrderEvent(OrderEvent event) {
        log.info("[Kafka] 이벤트 수신 — orderId={}, status={}", event.getOrderId(), event.getStatus());

        // Week 4: 실시간으로 프론트엔드에 주문 변경 이벤트 전송
        messagingTemplate.convertAndSend("/topic/orders", event);
    }
}
