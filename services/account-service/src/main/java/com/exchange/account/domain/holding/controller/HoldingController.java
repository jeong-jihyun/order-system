package com.exchange.account.domain.holding.controller;

import com.exchange.account.common.response.ApiResponse;
import com.exchange.account.domain.holding.dto.HoldingResponse;
import com.exchange.account.domain.holding.service.HoldingService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Holdings API", description = "보유 종목 조회")
@RestController
@RequestMapping("/api/v1/holdings")
@RequiredArgsConstructor
public class HoldingController {

    private final HoldingService holdingService;

    @Operation(summary = "내 보유 종목 조회")
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<List<HoldingResponse>>> getMyHoldings(
            @RequestHeader("X-User-Name") String username) {
        return ResponseEntity.ok(ApiResponse.success(holdingService.getMyHoldings(username)));
    }
}
