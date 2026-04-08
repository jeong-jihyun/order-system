package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 스탑-리밋 주문 전략
 * 트리거 가격 + 지정가 모두 필수
 */
@Slf4j
@Component
public class StopLimitOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getSupportedType() { return OrderType.STOP_LIMIT; }

    @Override
    public void validate(OrderRequest request) {
        if (request.getStopPrice() == null) {
            throw new IllegalArgumentException("스탑-리밋 주문은 트리거 가격(stopPrice)이 필수입니다.");
        }
        if (request.getTotalPrice() == null) {
            throw new IllegalArgumentException("스탑-리밋 주문은 지정가(totalPrice)가 필수입니다.");
        }
        log.debug("[StopLimit] 스탑-리밋 검증 통과 — stopPrice={}, price={}",
                request.getStopPrice(), request.getTotalPrice());
    }
}
