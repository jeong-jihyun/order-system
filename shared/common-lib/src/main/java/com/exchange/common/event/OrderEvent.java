package com.exchange.common.event;

import com.exchange.common.enums.OrderStatus;
import com.exchange.common.enums.OrderType;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import java.math.BigDecimal;

/**
 * 서비스 간 공유되는 주문 이벤트 (Kafka 메시지 페이로드)
 * shared/common-lib에 위치해 모든 서비스가 참조
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrderEvent extends BaseEvent {

    private Long orderId;
    private String customerName;
    private String productName;
    private Integer quantity;
    private BigDecimal totalPrice;
    private OrderType orderType;
    private OrderStatus status;

    @Override
    public String getEventType() { return "ORDER_EVENT"; }
}
