package com.exchange.order.domain.order.validator;

import com.exchange.order.domain.order.dto.OrderRequest;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

@Component
public class PriceValidator implements OrderValidator {
    private static final BigDecimal MAX_PRICE = new BigDecimal("1000000000");

    @Override
    public void validate(OrderRequest request) {
        if (request.getTotalPrice() == null || request.getTotalPrice().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("금액은 0보다 커야 합니다.");
        }
        if (request.getTotalPrice().compareTo(MAX_PRICE) > 0) {
            throw new IllegalArgumentException("금액은 10억 이하여야 합니다.");
        }
    }
}
