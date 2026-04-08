package com.exchange.account.domain.account.dto;

import com.exchange.account.domain.account.entity.Account;
import com.exchange.account.domain.account.entity.AccountType;
import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Builder
public class AccountResponse {
    private Long id;
    private String accountNumber;
    private AccountType accountType;
    private BigDecimal balance;
    private BigDecimal frozenBalance;
    private BigDecimal availableBalance;
    private boolean active;
    private LocalDateTime createdAt;

    public static AccountResponse from(Account account) {
        return AccountResponse.builder()
                .id(account.getId())
                .accountNumber(account.getAccountNumber())
                .accountType(account.getAccountType())
                .balance(account.getBalance())
                .frozenBalance(account.getFrozenBalance())
                .availableBalance(account.getBalance().subtract(account.getFrozenBalance()))
                .active(account.isActive())
                .createdAt(account.getCreatedAt())
                .build();
    }
}
