package com.order.kafka.event;

import com.order.domain.order.entity.Order;
import com.order.domain.order.entity.OrderStatus;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * [Week 2 - Kafka 이벤트 DTO]
 * Kafka 토픽으로 직렬화될 이벤트 객체.
 * Entity와 분리하여 외부 의존성 없이 직렬화 가능하게 설계.
 */
@Getter
@Setter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrderEvent {

    private Long orderId;
    private String customerName;
    private String productName;
    private Integer quantity;
    private BigDecimal totalPrice;
    private OrderStatus status;
    private LocalDateTime eventTime;

    public static OrderEvent of(Order order) {
        return OrderEvent.builder()
                .orderId(order.getId())
                .customerName(order.getCustomerName())
                .productName(order.getProductName())
                .quantity(order.getQuantity())
                .totalPrice(order.getTotalPrice())
                .status(order.getStatus())
                .eventTime(LocalDateTime.now())
                .build();
    }
}
