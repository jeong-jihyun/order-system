package com.exchange.order.domain.order.validator;

import com.exchange.order.domain.order.dto.OrderRequest;

@FunctionalInterface
public interface OrderValidator {
    void validate(OrderRequest request);

    default OrderValidator andThen(OrderValidator next) {
        return request -> {
            this.validate(request);
            next.validate(request);
        };
    }
}
