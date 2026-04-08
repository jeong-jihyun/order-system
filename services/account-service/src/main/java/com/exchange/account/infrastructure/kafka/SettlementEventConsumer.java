package com.exchange.account.infrastructure.kafka;

import com.exchange.account.domain.account.repository.AccountRepository;
import com.exchange.account.domain.holding.service.HoldingService;
import com.exchange.account.domain.user.repository.UserRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.Map;

/**
 * settlement-events 수신 — 정산 완료 후 잔고 반영 + 보유 종목 업데이트
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class SettlementEventConsumer {

    private final AccountRepository accountRepository;
    private final UserRepository userRepository;
    private final HoldingService holdingService;
    private final ObjectMapper objectMapper;

    @KafkaListener(topics = "settlement-events", groupId = "account-service-group")
    @Transactional
    public void consume(String message) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> payload = objectMapper.readValue(message, Map.class);

            String username   = (String) payload.get("username");
            String symbol     = (String) payload.get("symbol");
            String side       = (String) payload.get("side");
            BigDecimal netAmount = new BigDecimal(payload.get("netAmount").toString());

            log.info("[SettlementConsumer] 정산 이벤트 수신 — user={}, symbol={}, side={}, net={}",
                    username, symbol, side, netAmount);

            // 1. 잔고 반영: 매수(음수 netAmount=출금), 매도(양수 netAmount=입금)
            var user = userRepository.findByUsername(username).orElse(null);
            if (user != null) {
                var accounts = accountRepository.findByUserId(user.getId());
                var cashAccount = accounts.stream()
                        .filter(a -> a.getAccountType().name().equals("CASH"))
                        .findFirst().orElse(null);

                if (cashAccount != null) {
                    var locked = accountRepository.findByIdForUpdate(cashAccount.getId()).orElse(null);
                    if (locked != null) {
                        if (netAmount.compareTo(BigDecimal.ZERO) > 0) {
                            locked.deposit(netAmount);
                        } else if (netAmount.compareTo(BigDecimal.ZERO) < 0) {
                            locked.withdraw(netAmount.abs());
                        }
                        accountRepository.save(locked);
                        log.info("[잔고 반영] user={}, amount={}", username, netAmount);
                    }
                }
            }

            // 2. 보유 종목 업데이트
            // netAmount에서 executionPrice/quantity를 추출하기 위해 orderId로 조회 필요
            // 간략 구현: settlement-events에 포함된 정보로 처리
            Object priceObj = payload.get("executionPrice");
            Object qtyObj   = payload.get("executionQuantity");
            if (priceObj != null && qtyObj != null) {
                BigDecimal price = new BigDecimal(priceObj.toString());
                BigDecimal qty   = new BigDecimal(qtyObj.toString());
                holdingService.updateHolding(username, symbol, side, qty, price);
            }

        } catch (Exception e) {
            log.error("[SettlementConsumer] 처리 실패: {}", e.getMessage(), e);
        }
    }
}
