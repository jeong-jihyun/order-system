package com.order.domain.order.entity;

/**
 * 주문 상태 - State Machine 패턴
 * canTransitionTo()로 허용된 전이만 가능하도록 강제
 */
public enum OrderStatus {
    PENDING,     // 주문 대기
    PROCESSING,  // 처리 중
    COMPLETED,   // 완료
    CANCELLED;   // 취소

    /** 최종 상태 여부 (이후 전이 불가) */
    public boolean isTerminal() {
        return this == COMPLETED || this == CANCELLED;
    }

    /**
     * 상태 전이 유효성 검사
     * PENDING    -> PROCESSING | CANCELLED
     * PROCESSING -> COMPLETED  | CANCELLED
     */
    public boolean canTransitionTo(OrderStatus next) {
        return switch (this) {
            case PENDING    -> next == PROCESSING || next == CANCELLED;
            case PROCESSING -> next == COMPLETED  || next == CANCELLED;
            case COMPLETED, CANCELLED -> false;
        };
    }
}
