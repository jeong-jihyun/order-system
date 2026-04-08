package com.exchange.marketdata.domain.ohlcv.dto;

import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * OHLCV 캔들 데이터
 * Redis ZSet ohlcv:{symbol}:{interval} 에 score=timestamp 로 저장
 * interval: 1m, 5m, 15m, 1h, 1d
 */
@Getter
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class OhlcvDto {
    private String symbol;
    private String interval;
    private BigDecimal open;
    private BigDecimal high;
    private BigDecimal low;
    private BigDecimal close;
    private Long volume;
    private LocalDateTime openTime;
    private LocalDateTime closeTime;
}
