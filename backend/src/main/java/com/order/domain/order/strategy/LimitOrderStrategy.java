package com.order.domain.order.strategy;

import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.entity.OrderType;
import org.springframework.stereotype.Component;
import java.math.BigDecimal;

/**
 * [Strategy Pattern] 지정가 주문
 * - 지정 가격 이하일 때만 체결 (즉시 체결 불가)
 */
@Component
public class LimitOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getOrderType() { return OrderType.LIMIT; }

    @Override
    public BigDecimal calculateExecutionPrice(BigDecimal requestedPrice, BigDecimal marketPrice) {
        return requestedPrice; // 지정가 그대로
    }

    @Override
    public boolean isImmediateExecution() { return false; }

    @Override
    public void validate(OrderRequest request) {
        OrderStrategy.super.validate(request);
        if (request.getTotalPrice() == null || request.getTotalPrice().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("지정가 주문은 가격을 반드시 지정해야 합니다.");
        }
    }
}
