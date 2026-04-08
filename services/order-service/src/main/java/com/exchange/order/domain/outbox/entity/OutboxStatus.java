package com.exchange.order.domain.outbox.entity;

public enum OutboxStatus {
    PENDING,     // 발행 대기
    PUBLISHED,   // 발행 완료
    DEAD_LETTER  // 최대 재시도 초과 — 수동 개입 필요
}
