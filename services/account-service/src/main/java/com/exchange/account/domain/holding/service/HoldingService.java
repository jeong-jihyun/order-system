package com.exchange.account.domain.holding.service;

import com.exchange.account.domain.holding.dto.HoldingResponse;
import com.exchange.account.domain.holding.entity.Holding;
import com.exchange.account.domain.holding.repository.HoldingRepository;
import com.exchange.account.domain.user.entity.User;
import com.exchange.account.domain.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class HoldingService {

    private final HoldingRepository holdingRepository;
    private final UserRepository userRepository;

    @Transactional(readOnly = true)
    public List<HoldingResponse> getMyHoldings(String username) {
        User user = userRepository.findByUsername(username)
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다: " + username));
        return holdingRepository.findByUserId(user.getId()).stream()
                .filter(h -> h.getQuantity().compareTo(BigDecimal.ZERO) > 0)
                .map(HoldingResponse::from)
                .toList();
    }

    /**
     * 정산 완료 시 보유 종목 업데이트
     */
    public void updateHolding(String username, String symbol, String side,
                              BigDecimal quantity, BigDecimal price) {
        User user = userRepository.findByUsername(username).orElse(null);
        if (user == null) {
            log.warn("[보유종목] 사용자를 찾을 수 없습니다: {}", username);
            return;
        }

        Holding holding = holdingRepository.findByUserIdAndSymbolForUpdate(user.getId(), symbol)
                .orElse(null);

        if ("BUY".equalsIgnoreCase(side)) {
            if (holding == null) {
                holding = Holding.builder()
                        .user(user)
                        .symbol(symbol)
                        .build();
            }
            holding.buy(quantity, price);
            holdingRepository.save(holding);
            log.info("[보유종목 매수] user={}, symbol={}, qty={}, avgPrice={}",
                    username, symbol, holding.getQuantity(), holding.getAveragePrice());
        } else if ("SELL".equalsIgnoreCase(side)) {
            if (holding == null) {
                log.warn("[보유종목] 매도할 종목이 없습니다: user={}, symbol={}", username, symbol);
                return;
            }
            holding.sell(quantity);
            holdingRepository.save(holding);
            log.info("[보유종목 매도] user={}, symbol={}, remainQty={}",
                    username, symbol, holding.getQuantity());
        }
    }
}
