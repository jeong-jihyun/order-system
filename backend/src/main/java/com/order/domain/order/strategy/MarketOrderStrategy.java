package com.order.domain.order.strategy;

import com.order.domain.order.entity.OrderType;
import org.springframework.stereotype.Component;
import java.math.BigDecimal;

/**
 * [Strategy Pattern] 시장가 주문
 * - 즉시 체결, 현재 시장가로 실행
 */
@Component
public class MarketOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getOrderType() { return OrderType.MARKET; }

    @Override
    public BigDecimal calculateExecutionPrice(BigDecimal requestedPrice, BigDecimal marketPrice) {
        return marketPrice; // 시장가 = 현재가
    }

    @Override
    public boolean isImmediateExecution() { return true; }
}
