package com.exchange.trading.domain.matching.service;

import com.exchange.trading.domain.matching.dto.ExecutionResult;
import com.exchange.trading.domain.orderbook.entity.OrderBookEntry;
import com.exchange.trading.domain.orderbook.entity.OrderSide;
import com.exchange.trading.domain.orderbook.service.OrderBook;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.*;

/**
 * Price-Time Priority 매칭 엔진
 *
 * 매칭 알고리즘:
 * 1. 신규 BUY 주문 → bestAsk와 비교: BUY.price >= ASK.price → 체결
 * 2. 신규 SELL 주문 → bestBid와 비교: SELL.price <= BID.price → 체결
 * 3. 부분 체결 지원: 수량이 남으면 호가창에 잔량 유지
 * 4. MARKET 주문: 가격 조건 없이 반대편 최우선 호가와 즉시 체결
 *
 * Thread-Safety: 종목별 OrderBook 단위로 synchronized
 */
@Slf4j
@Component
public class MatchingEngine {

    /**
     * 신규 주문 매칭 시도
     * @return 체결 결과 목록 (복수 체결 가능 - 여러 가격 레벨에 걸친 체결)
     */
    public List<ExecutionResult> match(OrderBook orderBook, OrderBookEntry newOrder) {
        List<ExecutionResult> executions = new ArrayList<>();

        synchronized (orderBook) {
            if (newOrder.getSide() == OrderSide.BUY) {
                matchBuyOrder(orderBook, newOrder, executions);
            } else {
                matchSellOrder(orderBook, newOrder, executions);
            }

            // 미체결 잔량이 있으면 호가창에 등록 (지정가 주문만)
            if (!newOrder.isFilled() && newOrder.getPrice() != null) {
                orderBook.addOrder(newOrder);
            }
        }

        return executions;
    }

    private void matchBuyOrder(OrderBook book, OrderBookEntry buyOrder,
                                List<ExecutionResult> executions) {
        while (!buyOrder.isFilled()) {
            Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestAskOpt = book.bestAsk();
            if (bestAskOpt.isEmpty()) break;

            BigDecimal askPrice = bestAskOpt.get().getKey();
            // MARKET 주문이거나 BUY 지정가 >= ASK 가격이면 체결 가능
            boolean canMatch = buyOrder.getPrice() == null
                    || buyOrder.getPrice().compareTo(askPrice) >= 0;
            if (!canMatch) break;

            TreeSet<OrderBookEntry> askLevel = bestAskOpt.get().getValue();
            Iterator<OrderBookEntry> it = askLevel.iterator();
            if (!it.hasNext()) { book.removePriceLevel(OrderSide.SELL, askPrice); break; }

            OrderBookEntry sellOrder = it.next();
            BigDecimal fillQty = buyOrder.getRemainingQuantity()
                    .min(sellOrder.getRemainingQuantity());

            buyOrder.fill(fillQty);
            sellOrder.fill(fillQty);

            executions.add(ExecutionResult.builder()
                    .buyOrderId(buyOrder.getOrderId())
                    .sellOrderId(sellOrder.getOrderId())
                    .symbol(buyOrder.getSymbol())
                    .executionPrice(askPrice)
                    .executionQuantity(fillQty)
                    .executedAt(LocalDateTime.now())
                    .buyFilled(buyOrder.isFilled())
                    .sellFilled(sellOrder.isFilled())
                    .buyerUsername(buyOrder.getCustomerName())
                    .sellerUsername(sellOrder.getCustomerName())
                    .build());

            log.info("[체결] symbol={}, price={}, qty={}, buyId={}, sellId={}",
                    buyOrder.getSymbol(), askPrice, fillQty,
                    buyOrder.getOrderId(), sellOrder.getOrderId());

            if (sellOrder.isFilled()) {
                it.remove();
                if (askLevel.isEmpty()) book.removePriceLevel(OrderSide.SELL, askPrice);
            }
        }
    }

    private void matchSellOrder(OrderBook book, OrderBookEntry sellOrder,
                                 List<ExecutionResult> executions) {
        while (!sellOrder.isFilled()) {
            Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestBidOpt = book.bestBid();
            if (bestBidOpt.isEmpty()) break;

            BigDecimal bidPrice = bestBidOpt.get().getKey();
            // MARKET 주문이거나 SELL 지정가 <= BID 가격이면 체결 가능
            boolean canMatch = sellOrder.getPrice() == null
                    || sellOrder.getPrice().compareTo(bidPrice) <= 0;
            if (!canMatch) break;

            TreeSet<OrderBookEntry> bidLevel = bestBidOpt.get().getValue();
            Iterator<OrderBookEntry> it = bidLevel.iterator();
            if (!it.hasNext()) { book.removePriceLevel(OrderSide.BUY, bidPrice); break; }

            OrderBookEntry buyOrder = it.next();
            BigDecimal fillQty = sellOrder.getRemainingQuantity()
                    .min(buyOrder.getRemainingQuantity());

            sellOrder.fill(fillQty);
            buyOrder.fill(fillQty);

            executions.add(ExecutionResult.builder()
                    .buyOrderId(buyOrder.getOrderId())
                    .sellOrderId(sellOrder.getOrderId())
                    .symbol(sellOrder.getSymbol())
                    .executionPrice(bidPrice)
                    .executionQuantity(fillQty)
                    .executedAt(LocalDateTime.now())
                    .buyFilled(buyOrder.isFilled())
                    .sellFilled(sellOrder.isFilled())
                    .buyerUsername(buyOrder.getCustomerName())
                    .sellerUsername(sellOrder.getCustomerName())
                    .build());

            log.info("[체결] symbol={}, price={}, qty={}, buyId={}, sellId={}",
                    sellOrder.getSymbol(), bidPrice, fillQty,
                    buyOrder.getOrderId(), sellOrder.getOrderId());

            if (buyOrder.isFilled()) {
                it.remove();
                if (bidLevel.isEmpty()) book.removePriceLevel(OrderSide.BUY, bidPrice);
            }
        }
    }
}
