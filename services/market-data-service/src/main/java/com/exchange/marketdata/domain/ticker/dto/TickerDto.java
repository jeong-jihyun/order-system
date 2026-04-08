package com.exchange.marketdata.domain.ticker.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 현재 시세 스냅샷
 * WebSocket /topic/ticker/{symbol} 으로 브로드캐스트
 * Redis Hash ticker:{symbol} 에 저장
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
@JsonInclude(JsonInclude.Include.NON_NULL)
public class TickerDto {
    private String symbol;         // 종목 (예: AAPL, BTC-USD)
    private BigDecimal price;      // 현재가
    private BigDecimal open;       // 시가
    private BigDecimal high;       // 고가
    private BigDecimal low;        // 저가
    private BigDecimal prevClose;  // 전일 종가
    private BigDecimal change;     // 전일 대비 변동금액
    private BigDecimal changeRate; // 전일 대비 변동률(%)
    private Long volume;           // 거래량
    private BigDecimal turnover;   // 거래대금
    private LocalDateTime timestamp;
}
