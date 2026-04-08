package com.order.domain.order.validator;

import com.order.domain.order.dto.OrderRequest;

/**
 * [Chain of Responsibility Pattern]
 * 주문 검증 체인의 기본 인터페이스.
 * 각 검증기는 자신의 검증 후 다음 검증기로 forwarding.
 * OCP: 새 검증 규칙 추가 시 새 Validator 클래스와 체인 연결만 추가
 */
public interface OrderValidator {
    void validate(OrderRequest request);
    
    /** 다음 검증기 설정 후 this 반환 (Fluent API) */
    default OrderValidator andThen(OrderValidator next) {
        return request -> {
            this.validate(request);
            next.validate(request);
        };
    }
}
