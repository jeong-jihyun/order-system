package com.exchange.trading.domain.matching.service;

import com.exchange.trading.domain.matching.dto.ExecutionResult;
import com.exchange.trading.domain.orderbook.entity.OrderBookEntry;
import com.exchange.trading.domain.orderbook.entity.OrderSide;
import com.exchange.trading.domain.orderbook.service.OrderBook;
import com.exchange.trading.domain.orderbook.service.OrderBookRegistry;
import com.exchange.trading.infrastructure.kafka.ExecutionEventProducer;
import com.exchange.trading.infrastructure.redis.OrderBookSnapshotService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.List;

/**
 * 주문 접수 → 매칭 → 체결 이벤트 발행 → 호가창 스냅샷 저장
 * Kafka Consumer에서 호출
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ExecutionService {

    private final OrderBookRegistry registry;
    private final MatchingEngine matchingEngine;
    private final ExecutionEventProducer executionProducer;
    private final OrderBookSnapshotService snapshotService;
    private final StopOrderManager stopOrderManager;

    public void processOrder(Long orderId, String symbol, String side,
                             BigDecimal price, BigDecimal quantity, String customerName) {
        OrderSide orderSide = OrderSide.valueOf(side.toUpperCase());
        OrderBook orderBook = registry.getOrCreate(symbol);

        // MARKET 주문: price ≤ 0 → null
        BigDecimal orderPrice = (price == null || price.compareTo(BigDecimal.ZERO) <= 0) ? null : price;

        OrderBookEntry entry = OrderBookEntry.create(orderId, symbol, orderSide,
                                                      orderPrice, quantity, customerName);

        // 매칭 실행
        List<ExecutionResult> executions = matchingEngine.match(orderBook, entry);

        // 체결 결과 Kafka 발행
        for (ExecutionResult exec : executions) {
            executionProducer.publishExecution(exec);
        }

        // 호가창 스냅샷 Redis 저장
        snapshotService.saveSnapshot(orderBook);

        // 체결이 발생했으면 STOP 주문 트리거 확인
        if (!executions.isEmpty()) {
            BigDecimal lastPrice = executions.get(executions.size() - 1).getExecutionPrice();
            stopOrderManager.checkTriggers(symbol, lastPrice);
            log.info("[ExecutionService] {}건 체결 처리 완료 — symbol={}", executions.size(), symbol);
        }
    }
}
