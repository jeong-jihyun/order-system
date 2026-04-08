package com.order.domain.order.strategy;

import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.entity.OrderType;
import java.math.BigDecimal;

/**
 * [Strategy Pattern + ISP]
 * - OCP: 새 주문 타입 추가 시 이 인터페이스를 구현하는 클래스만 추가
 * - ISP: default 메서드로 공통 기본 동작 제공, 타입별 Override
 */
public interface OrderStrategy {
    /** 이 전략이 처리하는 주문 타입 */
    OrderType getOrderType();

    /** 주문 실행 가격 계산 */
    BigDecimal calculateExecutionPrice(BigDecimal requestedPrice, BigDecimal marketPrice);

    /** 즉시 체결 가능 여부 */
    boolean isImmediateExecution();

    /** 기본 유효성 검사 - Override 가능 */
    default void validate(OrderRequest request) {
        if (request.getQuantity() == null || request.getQuantity() <= 0) {
            throw new IllegalArgumentException("수량은 1 이상이어야 합니다.");
        }
    }
}
