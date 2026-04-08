package com.exchange.trading.domain.matching.service;

import com.exchange.trading.domain.orderbook.entity.OrderSide;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Lazy;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.CopyOnWriteArrayList;

/**
 * STOP 주문 관리자
 * - STOP_LOSS/STOP_LIMIT 주문을 대기 목록에 보관
 * - 체결이 발생할 때마다 lastPrice와 비교하여 트리거 조건 충족 시 시장가/지정가 주문으로 전환
 *
 * 트리거 조건:
 * - SELL STOP_LOSS: lastPrice <= stopPrice (가격 하락 시 손절)
 * - BUY STOP_LOSS:  lastPrice >= stopPrice (가격 상승 시 손절)
 * - STOP_LIMIT: 동일 조건에서 지정가 주문으로 전환
 */
@Slf4j
@Component
public class StopOrderManager {

    private final ExecutionService executionService;

    // symbol → 대기 중인 STOP 주문 목록
    private final ConcurrentHashMap<String, CopyOnWriteArrayList<StopOrderEntry>> pendingStops
            = new ConcurrentHashMap<>();

    @Autowired
    public StopOrderManager(@Lazy ExecutionService executionService) {
        this.executionService = executionService;
    }

    public void registerStopOrder(Long orderId, String symbol, String side,
                                   BigDecimal stopPrice, BigDecimal limitPrice,
                                   BigDecimal quantity, String orderType,
                                   String customerName) {
        StopOrderEntry entry = new StopOrderEntry(orderId, symbol, side, stopPrice,
                limitPrice, quantity, orderType, customerName);
        pendingStops.computeIfAbsent(symbol, k -> new CopyOnWriteArrayList<>()).add(entry);
        log.info("[StopOrder] 등록 — orderId={}, symbol={}, side={}, stopPrice={}, type={}",
                orderId, symbol, side, stopPrice, orderType);
    }

    /**
     * 체결 발생 시 호출 — lastPrice로 STOP 주문 트리거 확인
     */
    public void checkTriggers(String symbol, BigDecimal lastPrice) {
        CopyOnWriteArrayList<StopOrderEntry> stops = pendingStops.get(symbol);
        if (stops == null || stops.isEmpty()) return;

        List<StopOrderEntry> triggered = new ArrayList<>();
        for (StopOrderEntry entry : stops) {
            if (shouldTrigger(entry, lastPrice)) {
                triggered.add(entry);
            }
        }

        for (StopOrderEntry entry : triggered) {
            stops.remove(entry);
            // STOP_LOSS → 시장가 주문, STOP_LIMIT → 지정가 주문
            BigDecimal orderPrice = "STOP_LIMIT".equals(entry.orderType)
                    ? entry.limitPrice : BigDecimal.ZERO; // ZERO = MARKET
            String effectiveSide = entry.side;

            log.info("[StopOrder] 트리거! orderId={}, lastPrice={}, stopPrice={}, type={}",
                    entry.orderId, lastPrice, entry.stopPrice, entry.orderType);

            executionService.processOrder(
                    entry.orderId, entry.symbol, effectiveSide,
                    orderPrice, entry.quantity, entry.customerName);
        }
    }

    private boolean shouldTrigger(StopOrderEntry entry, BigDecimal lastPrice) {
        // SELL 손절: 가격이 stopPrice 이하로 떨어지면 트리거
        if ("SELL".equalsIgnoreCase(entry.side)) {
            return lastPrice.compareTo(entry.stopPrice) <= 0;
        }
        // BUY 손절: 가격이 stopPrice 이상으로 올라가면 트리거
        return lastPrice.compareTo(entry.stopPrice) >= 0;
    }

    public record StopOrderEntry(
            Long orderId, String symbol, String side,
            BigDecimal stopPrice, BigDecimal limitPrice,
            BigDecimal quantity, String orderType,
            String customerName) {}
}
