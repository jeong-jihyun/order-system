package com.exchange.account.infrastructure.kafka;

import com.exchange.account.domain.account.entity.AccountType;
import com.exchange.account.domain.account.repository.AccountRepository;
import com.exchange.account.domain.holding.service.HoldingService;
import com.exchange.account.domain.user.repository.UserRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;

/**
 * trading-engine 체결 이벤트(order-status-events) 구독
 * 체결 즉시 freeze 해제 + 잔고/보유종목 업데이트
 *
 * BUY 체결: unfreeze(amount) + CASH 차감 + STOCK holding 추가
 * SELL 체결: STOCK holding 차감 + CASH 증가
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class ExecutionEventConsumer {

    private final AccountRepository accountRepository;
    private final UserRepository userRepository;
    private final HoldingService holdingService;
    private final ObjectMapper objectMapper;

    @Transactional
    @KafkaListener(topics = "order-status-events", groupId = "account-execution-group")
    public void consume(String message) {
        try {
            JsonNode node = objectMapper.readTree(message);

            String symbol           = node.get("symbol").asText();
            BigDecimal price        = new BigDecimal(node.get("executionPrice").asText());
            BigDecimal qty          = new BigDecimal(node.get("executionQuantity").asText());
            BigDecimal totalAmount  = price.multiply(qty);
            String buyerUsername    = node.get("buyerUsername").asText();
            String sellerUsername   = node.get("sellerUsername").asText();
            boolean buyFilled       = node.get("buyFilled").asBoolean();
            boolean sellFilled      = node.get("sellFilled").asBoolean();

            log.info("[ExecutionConsumer] 체결 처리: symbol={}, price={}, qty={}, buyer={}, seller={}",
                    symbol, price, qty, buyerUsername, sellerUsername);

            // BUY 처리: 동결 해제 + 잔고 차감 + 보유종목 추가
            if (!buyerUsername.isEmpty()) {
                processBuy(buyerUsername, symbol, price, qty, totalAmount);
            }

            // SELL 처리: 보유종목 차감 + 잔고 증가
            if (!sellerUsername.isEmpty()) {
                processSell(sellerUsername, symbol, price, qty, totalAmount);
            }

        } catch (Exception e) {
            log.error("[ExecutionConsumer] 처리 실패: {}", e.getMessage(), e);
        }
    }

    private void processBuy(String username, String symbol, BigDecimal price,
                             BigDecimal qty, BigDecimal totalAmount) {
        try {
            var user = userRepository.findByUsername(username).orElse(null);
            if (user == null) { log.warn("[ExecutionConsumer] BUY 사용자 없음: {}", username); return; }

            var cashAccount = accountRepository.findByUserId(user.getId()).stream()
                    .filter(a -> a.getAccountType() == AccountType.CASH)
                    .findFirst().orElse(null);
            if (cashAccount == null) { log.warn("[ExecutionConsumer] CASH 계좌 없음: {}", username); return; }

            var locked = accountRepository.findByIdForUpdate(cashAccount.getId())
                    .orElseThrow(() -> new IllegalStateException("계좌 잠금 실패"));

            // unfreeze + 잔고 차감
            locked.unfreeze(totalAmount);
            locked.withdraw(totalAmount);
            accountRepository.save(locked);
            log.info("[ExecutionConsumer] BUY 잔고처리: user={}, 차감={}", username, totalAmount);

            // 보유종목 추가
            holdingService.updateHolding(username, symbol, "BUY", qty, price);
        } catch (Exception e) {
            log.error("[ExecutionConsumer] BUY 처리 실패: user={}, error={}", username, e.getMessage());
        }
    }

    private void processSell(String username, String symbol, BigDecimal price,
                              BigDecimal qty, BigDecimal totalAmount) {
        try {
            // 보유종목 차감
            holdingService.updateHolding(username, symbol, "SELL", qty, price);

            var user = userRepository.findByUsername(username).orElse(null);
            if (user == null) { log.warn("[ExecutionConsumer] SELL 사용자 없음: {}", username); return; }

            var cashAccount = accountRepository.findByUserId(user.getId()).stream()
                    .filter(a -> a.getAccountType() == AccountType.CASH)
                    .findFirst().orElse(null);
            if (cashAccount == null) { log.warn("[ExecutionConsumer] CASH 계좌 없음: {}", username); return; }

            var locked = accountRepository.findByIdForUpdate(cashAccount.getId())
                    .orElseThrow(() -> new IllegalStateException("계좌 잠금 실패"));

            // 잔고 증가
            locked.deposit(totalAmount);
            accountRepository.save(locked);
            log.info("[ExecutionConsumer] SELL 잔고처리: user={}, 증가={}", username, totalAmount);
        } catch (Exception e) {
            log.error("[ExecutionConsumer] SELL 처리 실패: user={}, error={}", username, e.getMessage());
        }
    }
}
