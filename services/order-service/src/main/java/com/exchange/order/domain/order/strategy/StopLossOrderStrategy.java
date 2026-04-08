package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

/**
 * 손절 주문 (Stop-Loss) 전략
 * 트리거 가격 필수, 체결가는 시장가로 결정
 */
@Slf4j
@Component
public class StopLossOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getSupportedType() { return OrderType.STOP_LOSS; }

    @Override
    public void validate(OrderRequest request) {
        if (request.getStopPrice() == null) {
            throw new IllegalArgumentException("손절 주문은 트리거 가격(stopPrice)이 필수입니다.");
        }
        log.debug("[StopLoss] 손절 주문 검증 통과 — stopPrice={}", request.getStopPrice());
    }
}
