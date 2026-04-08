package com.order.kafka.listener;

import com.order.domain.order.event.OrderCreatedEvent;
import com.order.domain.order.event.OrderStatusChangedEvent;
import com.order.kafka.event.OrderEvent;
import com.order.kafka.producer.OrderEventProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * [Observer Pattern - Spring EventListener]
 * 도메인 이벤트를 구독하여 Kafka 발행 처리.
 * SRP: 도메인 서비스는 이벤트만 발행, Kafka 발행 책임은 이 클래스에 위임
 * DIP: 서비스가 KafkaProducer에 직접 의존하지 않음
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderEventListener {

    private final OrderEventProducer orderEventProducer;

    @Async
    @EventListener
    public void handleOrderCreated(OrderCreatedEvent event) {
        log.info("[Event] 주문 생성 이벤트 수신 orderId={}", event.getOrderId());
        OrderEvent kafkaEvent = OrderEvent.builder()
                .orderId(event.getOrderId())
                .customerName(event.getCustomerName())
                .productName(event.getProductName())
                .eventTime(LocalDateTime.now())
                .build();
        orderEventProducer.sendOrderEvent(kafkaEvent);
    }

    @Async
    @EventListener
    public void handleOrderStatusChanged(OrderStatusChangedEvent event) {
        log.info("[Event] 상태 변경 이벤트 수신 orderId={}, {} -> {}",
                event.getOrderId(), event.getPreviousStatus(), event.getNewStatus());
    }
}
