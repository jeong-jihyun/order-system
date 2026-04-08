package com.exchange.account.domain.account.controller;

import com.exchange.account.common.response.ApiResponse;
import com.exchange.account.domain.account.dto.AccountResponse;
import com.exchange.account.domain.account.dto.BalanceRequest;
import com.exchange.account.domain.account.dto.CreateAccountRequest;
import com.exchange.account.domain.account.dto.FreezeRequest;
import com.exchange.account.domain.account.service.AccountService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
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
            @RequestHeader("X-User-Name") String username) {
        return ResponseEntity.ok(ApiResponse.success(accountService.getMyAccounts(username)));
    }

    @Operation(summary = "계좌 추가 생성")
    @PostMapping
    public ResponseEntity<ApiResponse<AccountResponse>> createAccount(
            @RequestHeader("X-User-Name") String username,
            @Valid @RequestBody CreateAccountRequest request) {
        AccountResponse created = accountService.createAccount(username, request.getAccountType());
        return ResponseEntity.status(HttpStatus.CREATED)
                .body(ApiResponse.success("계좌가 생성되었습니다", created));
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

    @Operation(summary = "증거금 동결 (내부 서비스 호출용)")
    @PostMapping("/freeze")
    public ResponseEntity<ApiResponse<String>> freeze(@Valid @RequestBody FreezeRequest request) {
        accountService.freezeForOrder(request.getUsername(), request.getAmount());
        return ResponseEntity.ok(ApiResponse.success("증거금 동결 완료", "OK"));
    }

    @Operation(summary = "증거금 해제 (내부 서비스 호출용)")
    @PostMapping("/unfreeze")
    public ResponseEntity<ApiResponse<String>> unfreeze(@Valid @RequestBody FreezeRequest request) {
        accountService.unfreezeForOrder(request.getUsername(), request.getAmount());
        return ResponseEntity.ok(ApiResponse.success("증거금 해제 완료", "OK"));
    }
}
