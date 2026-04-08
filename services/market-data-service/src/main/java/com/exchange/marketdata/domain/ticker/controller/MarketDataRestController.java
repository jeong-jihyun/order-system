package com.exchange.marketdata.domain.ticker.controller;

import com.exchange.marketdata.common.response.ApiResponse;
import com.exchange.marketdata.domain.ohlcv.dto.OhlcvDto;
import com.exchange.marketdata.domain.ohlcv.service.OhlcvService;
import com.exchange.marketdata.domain.ticker.dto.TickerDto;
import com.exchange.marketdata.domain.ticker.service.TickerService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Market Data API", description = "실시간 시세 / OHLCV 조회")
@RestController
@RequestMapping("/api/v1/market")
@RequiredArgsConstructor
public class MarketDataRestController {

    private final TickerService tickerService;
    private final OhlcvService ohlcvService;

    @Operation(summary = "현재 시세 조회")
    @GetMapping("/ticker/{symbol}")
    public ResponseEntity<ApiResponse<TickerDto>> getTicker(@PathVariable String symbol) {
        TickerDto ticker = tickerService.getTicker(symbol)
                .orElseThrow(() -> new IllegalArgumentException("시세 정보가 없습니다: " + symbol));
        return ResponseEntity.ok(ApiResponse.success(ticker));
    }

    @Operation(summary = "OHLCV 캔들 조회")
    @GetMapping("/ohlcv/{symbol}")
    public ResponseEntity<ApiResponse<List<OhlcvDto>>> getOhlcv(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "1m") String interval,
            @RequestParam(defaultValue = "100") int limit) {
        List<OhlcvDto> candles = ohlcvService.getCandles(symbol, interval,
                Math.min(limit, 500));
        return ResponseEntity.ok(ApiResponse.success(candles));
    }
}
