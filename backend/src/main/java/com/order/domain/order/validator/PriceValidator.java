package com.order.domain.order.validator;

import com.order.domain.order.dto.OrderRequest;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

/**
 * [Chain of Responsibility] 가격 검증기
 */
@Component
public class PriceValidator implements OrderValidator {
    private static final BigDecimal MAX_PRICE = new BigDecimal("1000000000"); // 10억

    @Override
    public void validate(OrderRequest request) {
        if (request.getTotalPrice() == null || request.getTotalPrice().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("주문 금액은 0보다 커야 합니다.");
        }
        if (request.getTotalPrice().compareTo(MAX_PRICE) > 0) {
            throw new IllegalArgumentException("단일 주문 최대 금액은 10억원입니다.");
        }
    }
}
