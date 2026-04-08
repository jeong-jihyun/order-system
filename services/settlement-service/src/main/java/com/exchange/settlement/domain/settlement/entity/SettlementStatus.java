package com.exchange.settlement.domain.settlement.entity;

/**
 * 정산 상태 머신
 * PENDING → SCHEDULED → COMPLETED
 *                     → FAILED (재시도 후 실패)
 */
public enum SettlementStatus {
    PENDING,     // 체결 완료, 정산 대기
    SCHEDULED,   // T+2 정산일 확정
    COMPLETED,   // 잔고 반영 완료
    FAILED       // 정산 실패 (수동 처리 필요)
}
