package com.exchange.account.domain.account.dto;

import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.math.BigDecimal;

@Getter
@NoArgsConstructor
@AllArgsConstructor
public class BalanceRequest {

    @NotNull(message = "금액은 필수입니다")
    @DecimalMin(value = "0.01", message = "금액은 0.01 이상이어야 합니다")
    @DecimalMax(value = "1000000000", message = "금액은 10억 이하여야 합니다")
    private BigDecimal amount;
}
