package com.exchange.order.domain.order.dto;

import com.exchange.order.domain.order.entity.OrderType;
import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.math.BigDecimal;

@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OrderRequest {

    @NotBlank(message = "고객명은 필수입니다")
    @Size(max = 50, message = "고객명은 50자 이하여야 합니다")
    private String customerName;

    @NotBlank(message = "상품명은 필수입니다")
    @Size(max = 100, message = "상품명은 100자 이하여야 합니다")
    private String productName;

    @NotNull(message = "수량은 필수입니다")
    @Positive(message = "수량은 양수여야 합니다")
    @Max(value = 10000, message = "수량은 10,000 이하여야 합니다")
    private Integer quantity;

    @NotNull(message = "총 금액은 필수입니다")
    @Positive(message = "총 금액은 양수여야 합니다")
    @DecimalMax(value = "1000000000", message = "금액은 10억 이하여야 합니다")
    private BigDecimal totalPrice;

    private OrderType orderType;

    /** STOP 주문 트리거 가격 (STOP_LOSS/STOP_LIMIT 전용) */
    private BigDecimal stopPrice;

    /** 주문 방향: BUY(매수) | SELL(매도). 기본값 BUY */
    @Builder.Default
    private String side = "BUY";
}
