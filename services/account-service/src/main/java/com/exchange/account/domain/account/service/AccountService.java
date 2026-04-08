package com.exchange.account.domain.account.service;

import com.exchange.account.domain.account.dto.AccountResponse;
import com.exchange.account.domain.account.dto.BalanceRequest;
import com.exchange.account.domain.account.repository.AccountRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class AccountService {

    private final AccountRepository accountRepository;

    @Transactional(readOnly = true)
    public List<AccountResponse> getMyAccounts(Long userId) {
        return accountRepository.findByUserId(userId).stream()
                .map(AccountResponse::from)
                .toList();
    }

    @Transactional(readOnly = true)
    public AccountResponse getAccount(Long accountId) {
        return accountRepository.findById(accountId)
                .map(AccountResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("계좌를 찾을 수 없습니다. id=" + accountId));
    }

    public AccountResponse deposit(Long accountId, BalanceRequest request) {
        var account = accountRepository.findByIdForUpdate(accountId)
                .orElseThrow(() -> new IllegalArgumentException("계좌를 찾을 수 없습니다."));
        account.deposit(request.getAmount());
        log.info("[입금] accountId={}, amount={}", accountId, request.getAmount());
        return AccountResponse.from(accountRepository.save(account));
    }

    public AccountResponse withdraw(Long accountId, BalanceRequest request) {
        var account = accountRepository.findByIdForUpdate(accountId)
                .orElseThrow(() -> new IllegalArgumentException("계좌를 찾을 수 없습니다."));
        account.withdraw(request.getAmount());
        log.info("[출금] accountId={}, amount={}", accountId, request.getAmount());
        return AccountResponse.from(accountRepository.save(account));
    }
}
