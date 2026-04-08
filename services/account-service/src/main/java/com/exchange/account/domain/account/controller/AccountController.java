package com.exchange.account.domain.account.controller;

import com.exchange.account.common.response.ApiResponse;
import com.exchange.account.domain.account.dto.AccountResponse;
import com.exchange.account.domain.account.dto.BalanceRequest;
import com.exchange.account.domain.account.service.AccountService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Account API", description = "계좌/잔고 관리")
@RestController
@RequestMapping("/api/v1/accounts")
@RequiredArgsConstructor
public class AccountController {

    private final AccountService accountService;

    @Operation(summary = "내 계좌 목록 조회")
    @GetMapping("/me")
    public ResponseEntity<ApiResponse<List<AccountResponse>>> getMyAccounts(
            @RequestHeader("X-User-Name") String username,
            @RequestHeader(value = "X-User-Role", defaultValue = "USER") String role) {
        // Gateway에서 X-User-Name 헤더로 전달된 userId 기반 조회
        // Phase 3에서는 username → userId 조회 구현 예정
        return ResponseEntity.ok(ApiResponse.success(List.of()));
    }

    @Operation(summary = "계좌 단건 조회")
    @GetMapping("/{id}")
    public ResponseEntity<ApiResponse<AccountResponse>> getAccount(@PathVariable Long id) {
        return ResponseEntity.ok(ApiResponse.success(accountService.getAccount(id)));
    }

    @Operation(summary = "입금")
    @PostMapping("/{id}/deposit")
    public ResponseEntity<ApiResponse<AccountResponse>> deposit(
            @PathVariable Long id,
            @Valid @RequestBody BalanceRequest request) {
        return ResponseEntity.ok(ApiResponse.success("입금 완료", accountService.deposit(id, request)));
    }

    @Operation(summary = "출금")
    @PostMapping("/{id}/withdraw")
    public ResponseEntity<ApiResponse<AccountResponse>> withdraw(
            @PathVariable Long id,
            @Valid @RequestBody BalanceRequest request) {
        return ResponseEntity.ok(ApiResponse.success("출금 완료", accountService.withdraw(id, request)));
    }
}
