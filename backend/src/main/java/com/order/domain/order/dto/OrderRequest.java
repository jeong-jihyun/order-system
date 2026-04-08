package com.order.domain.order.dto;

import com.order.domain.order.entity.OrderType;
import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Getter
@NoArgsConstructor
public class OrderRequest {

    @NotBlank(message = "고객명은 필수입니다.")
    @Size(max = 50, message = "고객명은 50자 이하여야 합니다.")
    private String customerName;

    @NotBlank(message = "상품명은 필수입니다.")
    @Size(max = 100, message = "상품명은 100자 이하여야 합니다.")
    private String productName;

    @NotNull(message = "수량은 필수입니다.")
    @Min(value = 1, message = "수량은 1 이상이어야 합니다.")
    private Integer quantity;

    @NotNull(message = "금액은 필수입니다.")
    @DecimalMin(value = "0.01", message = "금액은 0보다 커야 합니다.")
    private BigDecimal totalPrice;

    /** 주문 타입 - null이면 LIMIT 기본값 적용 */
    private OrderType orderType;
}
