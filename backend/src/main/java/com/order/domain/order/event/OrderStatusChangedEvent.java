package com.order.domain.order.event;

import com.order.domain.order.entity.OrderStatus;
import lombok.Getter;
import org.springframework.context.ApplicationEvent;

import java.time.LocalDateTime;

/**
 * [Observer Pattern] 주문 상태 변경 도메인 이벤트
 */
@Getter
public class OrderStatusChangedEvent extends ApplicationEvent {

    private final Long orderId;
    private final OrderStatus previousStatus;
    private final OrderStatus newStatus;
    private final LocalDateTime occurredAt;

    public OrderStatusChangedEvent(Object source, Long orderId,
                                   OrderStatus previousStatus, OrderStatus newStatus) {
        super(source);
        this.orderId = orderId;
        this.previousStatus = previousStatus;
        this.newStatus = newStatus;
        this.occurredAt = LocalDateTime.now();
    }
}
