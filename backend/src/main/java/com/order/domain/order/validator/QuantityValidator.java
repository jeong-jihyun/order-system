package com.order.domain.order.validator;

import com.order.domain.order.dto.OrderRequest;
import org.springframework.stereotype.Component;

/**
 * [Chain of Responsibility] 수량 검증기
 */
@Component
public class QuantityValidator implements OrderValidator {
    private static final int MAX_QUANTITY = 10_000;

    @Override
    public void validate(OrderRequest request) {
        if (request.getQuantity() == null || request.getQuantity() <= 0) {
            throw new IllegalArgumentException("수량은 1 이상이어야 합니다.");
        }
        if (request.getQuantity() > MAX_QUANTITY) {
            throw new IllegalArgumentException("단일 주문 최대 수량은 " + MAX_QUANTITY + "개입니다.");
        }
    }
}
