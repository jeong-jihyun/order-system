package com.exchange.settlement.domain.settlement.entity;

import jakarta.persistence.*;
import lombok.*;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalDateTime;

/**
 * 체결 1건당 1개의 정산 레코드 생성
 * 매수/매도 각각 별도 레코드 (수수료/세금 계산이 다름)
 */
@Entity
@Table(name = "settlement_records",
       indexes = {
           @Index(name = "idx_order_id",         columnList = "orderId"),
           @Index(name = "idx_settlement_date",   columnList = "settlementDate,status"),
           @Index(name = "idx_username",          columnList = "username")
       })
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SettlementRecord {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private Long orderId;

    @Column(nullable = false)
    private Long counterOrderId;     // 상대방 주문 ID

    @Column(nullable = false)
    private String username;

    @Column(nullable = false, length = 20)
    private String symbol;

    @Column(nullable = false, length = 10)
    private String side;             // BUY / SELL

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal executionPrice;

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal executionQuantity;

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal grossAmount;  // 체결 금액 (price * quantity)

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal commission;   // 수수료

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal tax;          // 거래세 (매도만)

    @Column(nullable = false, precision = 20, scale = 8)
    private BigDecimal netAmount;    // 실수령/실지불 금액 (grossAmount ± commission ± tax)

    @Column(nullable = false)
    private LocalDate settlementDate;  // T+2 정산 예정일

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private SettlementStatus status;

    @Column(nullable = false)
    private LocalDateTime executedAt;

    private LocalDateTime settledAt;   // 실제 정산 처리 시각

    public void markScheduled() {
        this.status = SettlementStatus.SCHEDULED;
    }

    public void markCompleted() {
        this.status = SettlementStatus.COMPLETED;
        this.settledAt = LocalDateTime.now();
    }

    public void markFailed() {
        this.status = SettlementStatus.FAILED;
    }
}
