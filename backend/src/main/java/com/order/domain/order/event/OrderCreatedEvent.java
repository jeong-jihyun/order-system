package com.order.domain.order.event;

import com.order.domain.order.entity.Order;
import lombok.Getter;
import org.springframework.context.ApplicationEvent;

import java.time.LocalDateTime;

/**
 * [Observer Pattern - Spring ApplicationEvent]
 * 주문 생성 도메인 이벤트.
 * OrderCommandService는 이벤트만 발행 -> Kafka 발행은 리스너가 담당
 * SRP: 서비스는 비즈니스 로직만, 인프라 관심사는 리스너로 분리
 */
@Getter
public class OrderCreatedEvent extends ApplicationEvent {

    private final Long orderId;
    private final String customerName;
    private final String productName;
    private final LocalDateTime occurredAt;

    public OrderCreatedEvent(Object source, Order order) {
        super(source);
        this.orderId = order.getId();
        this.customerName = order.getCustomerName();
        this.productName = order.getProductName();
        this.occurredAt = LocalDateTime.now();
    }
}
