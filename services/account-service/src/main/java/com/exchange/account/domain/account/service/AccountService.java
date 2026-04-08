package com.exchange.account.domain.account.service;

import com.exchange.account.domain.account.dto.AccountResponse;
import com.exchange.account.domain.account.dto.BalanceRequest;
import com.exchange.account.domain.account.entity.Account;
import com.exchange.account.domain.account.entity.AccountType;
import com.exchange.account.domain.account.repository.AccountRepository;
import com.exchange.account.domain.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.UUID;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class AccountService {

    private final AccountRepository accountRepository;
    private final UserRepository userRepository;

    @Transactional(readOnly = true)
    public List<AccountResponse> getMyAccounts(String username) {
        var user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + username));
        return accountRepository.findByUserId(user.getId()).stream()
                .map(AccountResponse::from)
                .toList();
    }

    public AccountResponse createAccount(String username, AccountType accountType) {
        var user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + username));
        Account account = Account.builder()
                .user(user)
                .accountNumber("ACC" + UUID.randomUUID().toString().replace("-", "").substring(0, 9).toUpperCase())
                .accountType(accountType)
                .build();
        Account saved = accountRepository.save(account);
        log.info("[계좌생성] userId={}, type={}, number={}", user.getId(), accountType, saved.getAccountNumber());
        return AccountResponse.from(saved);
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

    /**
     * 주문 접수 시 잔고 동결 (매수 증거금)
     */
    public void freezeForOrder(String username, java.math.BigDecimal amount) {
        var user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + username));
        var accounts = accountRepository.findByUserId(user.getId());
        var cashAccount = accounts.stream()
                .filter(a -> a.getAccountType() == AccountType.CASH)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("현금 계좌가 없습니다."));
        var locked = accountRepository.findByIdForUpdate(cashAccount.getId())
                .orElseThrow(() -> new IllegalStateException("계좌 잠금 실패"));
        locked.freeze(amount);
        accountRepository.save(locked);
        log.info("[증거금 동결] user={}, amount={}", username, amount);
    }

    /**
     * 주문 취소 시 동결 해제
     */
    public void unfreezeForOrder(String username, java.math.BigDecimal amount) {
        var user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + username));
        var accounts = accountRepository.findByUserId(user.getId());
        var cashAccount = accounts.stream()
                .filter(a -> a.getAccountType() == AccountType.CASH)
                .findFirst()
                .orElseThrow(() -> new IllegalStateException("현금 계좌가 없습니다."));
        var locked = accountRepository.findByIdForUpdate(cashAccount.getId())
                .orElseThrow(() -> new IllegalStateException("계좌 잠금 실패"));
        locked.unfreeze(amount);
        accountRepository.save(locked);
        log.info("[증거금 해제] user={}, amount={}", username, amount);
    }
}
