package com.exchange.account.domain.account.dto;

import com.exchange.account.domain.account.entity.AccountType;
import jakarta.validation.constraints.NotNull;
import lombok.AllArgsConstructor;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class CreateAccountRequest {

    @NotNull(message = "계좌 유형은 필수입니다 (CASH, STOCK, DERIVATIVE)")
    private AccountType accountType;
}
