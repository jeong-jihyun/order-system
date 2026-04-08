package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class LimitOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getSupportedType() { return OrderType.LIMIT; }

    @Override
    public void validate(OrderRequest request) {
        if (request.getTotalPrice() == null) {
            throw new IllegalArgumentException("지정가 주문은 가격이 필수입니다.");
        }
        log.debug("[LimitOrder] 지정가 주문 검증 통과 — price={}", request.getTotalPrice());
    }
}
