package com.exchange.account.domain.holding.dto;

import com.exchange.account.domain.holding.entity.Holding;
import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Builder
public class HoldingResponse {
    private Long id;
    private String symbol;
    private BigDecimal quantity;
    private BigDecimal averagePrice;
    private BigDecimal totalInvestment;
    private LocalDateTime updatedAt;

    public static HoldingResponse from(Holding holding) {
        return HoldingResponse.builder()
                .id(holding.getId())
                .symbol(holding.getSymbol())
                .quantity(holding.getQuantity())
                .averagePrice(holding.getAveragePrice())
                .totalInvestment(holding.getTotalInvestment())
                .updatedAt(holding.getUpdatedAt())
                .build();
    }
}
