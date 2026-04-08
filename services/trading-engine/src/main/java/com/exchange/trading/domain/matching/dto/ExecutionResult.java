package com.exchange.trading.domain.matching.dto;

import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 단일 체결 결과
 * - buyOrderId/sellOrderId: 매수/매도 주문 ID
 * - executionPrice: 체결가 (매도 호가 기준)
 * - executionQuantity: 체결 수량
 */
@Getter
@Builder
public class ExecutionResult {
    private final Long buyOrderId;
    private final Long sellOrderId;
    private final String symbol;
    private final BigDecimal executionPrice;
    private final BigDecimal executionQuantity;
    private final LocalDateTime executedAt;
    private final boolean buyFilled;   // 매수 주문 완전 체결 여부
    private final boolean sellFilled;  // 매도 주문 완전 체결 여부
}
