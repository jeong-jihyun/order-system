package com.exchange.account.domain.account.entity;

import com.exchange.account.domain.user.entity.User;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Table(name = "accounts")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Account {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(nullable = false, unique = true, length = 20)
    private String accountNumber;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private AccountType accountType = AccountType.CASH;

    @Column(nullable = false, precision = 18, scale = 2)
    @Builder.Default
    private BigDecimal balance = BigDecimal.ZERO;

    @Column(nullable = false, precision = 18, scale = 2)
    @Builder.Default
    private BigDecimal frozenBalance = BigDecimal.ZERO; // 주문 중 동결 금액

    @Column(nullable = false)
    @Builder.Default
    private boolean active = true;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    /**
     * 잔고 입금
     */
    public void deposit(BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0)
            throw new IllegalArgumentException("입금 금액은 양수여야 합니다.");
        this.balance = this.balance.add(amount);
    }

    /**
     * 잔고 출금 — 가용 잔고(balance - frozenBalance) 기준 검증
     */
    public void withdraw(BigDecimal amount) {
        if (amount.compareTo(BigDecimal.ZERO) <= 0)
            throw new IllegalArgumentException("출금 금액은 양수여야 합니다.");
        BigDecimal available = this.balance.subtract(this.frozenBalance);
        if (available.compareTo(amount) < 0)
            throw new IllegalStateException("잔고가 부족합니다. 가용잔고=" + available);
        this.balance = this.balance.subtract(amount);
    }

    /**
     * 주문용 잔고 동결 (주문 접수 시)
     */
    public void freeze(BigDecimal amount) {
        BigDecimal available = this.balance.subtract(this.frozenBalance);
        if (available.compareTo(amount) < 0)
            throw new IllegalStateException("동결 가능 잔고가 부족합니다.");
        this.frozenBalance = this.frozenBalance.add(amount);
    }

    /**
     * 동결 해제 (주문 취소/체결 완료 시)
     */
    public void unfreeze(BigDecimal amount) {
        if (this.frozenBalance.compareTo(amount) < 0)
            throw new IllegalStateException("동결 잔고보다 큰 금액을 해제할 수 없습니다.");
        this.frozenBalance = this.frozenBalance.subtract(amount);
    }
}
