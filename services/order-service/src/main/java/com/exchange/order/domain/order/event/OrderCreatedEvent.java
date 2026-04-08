package com.exchange.order.domain.order.event;

import com.exchange.order.domain.order.entity.Order;
import lombok.Getter;
import org.springframework.context.ApplicationEvent;

@Getter
public class OrderCreatedEvent extends ApplicationEvent {
    private final Long orderId;
    private final String customerName;
    private final String productName;
    private final String aggregateType = "Order";

    public OrderCreatedEvent(Object source, Order order) {
        super(source);
        this.orderId = order.getId();
        this.customerName = order.getCustomerName();
        this.productName = order.getProductName();
    }
}
