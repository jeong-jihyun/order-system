package com.exchange.order.domain.order.entity;

public enum OrderType {
    MARKET,     // 시장가 주문 — 즉시 체결, 가격 지정 없음
    LIMIT,      // 지정가 주문 — 지정가 이하/이상에서만 체결
    STOP_LOSS,  // 손절 주문 — 트리거 가격 도달 시 시장가로 전환
    STOP_LIMIT  // 스탑-리밋 — 트리거 가격 도달 시 지정가로 전환
}
