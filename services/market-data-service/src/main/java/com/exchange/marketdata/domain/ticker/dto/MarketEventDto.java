package com.exchange.marketdata.domain.ticker.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.math.BigDecimal;

/**
 * Kafka에서 수신하는 체결 이벤트 페이로드
 * order-service의 Outbox에서 발행된 JSON 역직렬화 대상
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class MarketEventDto {
    private Long orderId;
    private String productName;  // 종목명(심볼)
    private Integer quantity;
    private BigDecimal totalPrice;
    private String status;
    private String orderType;
}
