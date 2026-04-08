package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.entity.OrderType;

public interface OrderStrategy {
    OrderType getSupportedType();
    void validate(OrderRequest request);

    default void preProcess(OrderRequest request) {}
    default void postProcess(Long orderId) {}
}
