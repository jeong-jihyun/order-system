package com.order.domain.order.entity;

/**
 * 주문 타입 - Strategy 패턴의 타입 식별자
 * OCP: 새 주문 타입 추가 시 이 enum과 새 Strategy 클래스만 추가
 */
public enum OrderType {
    MARKET,       // 시장가 주문 - 즉시 체결, 가격 지정 불가
    LIMIT,        // 지정가 주문 - 지정 가격 이하에서만 체결
    STOP_LOSS,    // 손절 주문 - 특정 가격 하락 시 자동 매도
    STOP_LIMIT    // 스톱리밋 - 스톱 가격 도달 시 지정가 주문 전환
}
