package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class MarketOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getSupportedType() { return OrderType.MARKET; }

    @Override
    public void validate(OrderRequest request) {
        // 시장가 주문: 가격은 Trading Engine이 결정하므로 별도 검증 없음
        log.debug("[MarketOrder] 시장가 주문 검증 통과 — qty={}", request.getQuantity());
    }

    @Override
    public void postProcess(Long orderId) {
        log.info("[MarketOrder] 시장가 즉시 체결 요청 전송 — orderId={}", orderId);
    }
}
