package com.exchange.account.domain.holding.entity;

import com.exchange.account.domain.user.entity.User;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDateTime;

/**
 * 보유 종목 (포트폴리오)
 * 정산 완료 이벤트 수신 시 매수/매도에 따라 수량 및 평균 단가 업데이트
 */
@Entity
@Table(name = "holdings",
       uniqueConstraints = @UniqueConstraint(columnNames = {"user_id", "symbol"}),
       indexes = @Index(name = "idx_holding_user", columnList = "user_id"))
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Holding {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false, length = 20)
    private String symbol;

    @Column(nullable = false, precision = 20, scale = 8)
    @Builder.Default
    private BigDecimal quantity = BigDecimal.ZERO;

    @Column(nullable = false, precision = 20, scale = 8)
    @Builder.Default
    private BigDecimal averagePrice = BigDecimal.ZERO;

    @Column(nullable = false, precision = 20, scale = 2)
    @Builder.Default
    private BigDecimal totalInvestment = BigDecimal.ZERO;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    /**
     * 매수 시 보유 종목 업데이트 (이동평균 단가 계산)
     */
    public void buy(BigDecimal buyQuantity, BigDecimal buyPrice) {
        BigDecimal newInvestment = buyPrice.multiply(buyQuantity);
        this.totalInvestment = this.totalInvestment.add(newInvestment);
        this.quantity = this.quantity.add(buyQuantity);
        if (this.quantity.compareTo(BigDecimal.ZERO) > 0) {
            this.averagePrice = this.totalInvestment
                    .divide(this.quantity, 8, RoundingMode.HALF_UP);
        }
    }

    /**
     * 매도 시 보유 종목 업데이트
     */
    public void sell(BigDecimal sellQuantity) {
        if (this.quantity.compareTo(sellQuantity) < 0) {
            throw new IllegalStateException("보유 수량 부족: 보유=" + this.quantity + ", 매도=" + sellQuantity);
        }
        BigDecimal ratio = sellQuantity.divide(this.quantity, 8, RoundingMode.HALF_UP);
        BigDecimal soldInvestment = this.totalInvestment.multiply(ratio).setScale(2, RoundingMode.HALF_UP);
        this.totalInvestment = this.totalInvestment.subtract(soldInvestment);
        this.quantity = this.quantity.subtract(sellQuantity);
        if (this.quantity.compareTo(BigDecimal.ZERO) <= 0) {
            this.quantity = BigDecimal.ZERO;
            this.averagePrice = BigDecimal.ZERO;
            this.totalInvestment = BigDecimal.ZERO;
        }
    }
}
