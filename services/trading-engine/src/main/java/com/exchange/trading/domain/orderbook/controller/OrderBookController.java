package com.exchange.trading.domain.orderbook.controller;

import com.exchange.trading.common.response.ApiResponse;
import com.exchange.trading.domain.orderbook.service.OrderBook;
import com.exchange.trading.domain.orderbook.service.OrderBookRegistry;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@Tag(name = "Order Book API", description = "호가창 조회")
@RestController
@RequestMapping("/api/v1/orderbook")
@RequiredArgsConstructor
public class OrderBookController {

    private final OrderBookRegistry registry;

    @Operation(summary = "호가창 스냅샷 조회")
    @GetMapping("/{symbol}")
    public ResponseEntity<ApiResponse<OrderBook.OrderBookSnapshot>> getSnapshot(
            @PathVariable String symbol,
            @RequestParam(defaultValue = "10") int depth) {
        OrderBook book = registry.getOrCreate(symbol);
        return ResponseEntity.ok(ApiResponse.success(book.getSnapshot(depth)));
    }
}
