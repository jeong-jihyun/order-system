package com.exchange.settlement.domain.settlement.controller;

import com.exchange.settlement.common.response.ApiResponse;
import com.exchange.settlement.domain.settlement.entity.SettlementRecord;
import com.exchange.settlement.domain.settlement.repository.SettlementRecordRepository;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Settlement API", description = "정산 내역 조회")
@RestController
@RequestMapping("/api/v1/settlements")
@RequiredArgsConstructor
public class SettlementController {

    private final SettlementRecordRepository settlementRepo;

    @Operation(summary = "내 정산 내역 조회")
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<List<SettlementRecord>>> getMySettlements(
            @RequestHeader("X-User-Name") String username) {
        List<SettlementRecord> records =
                settlementRepo.findByUsernameOrderByExecutedAtDesc(username);
        return ResponseEntity.ok(ApiResponse.success(records));
    }
}
