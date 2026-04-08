package com.exchange.trading.domain.orderbook.service;

import com.exchange.trading.domain.orderbook.entity.OrderBookEntry;
import com.exchange.trading.domain.orderbook.entity.OrderSide;
import lombok.extern.slf4j.Slf4j;

import java.math.BigDecimal;
import java.util.*;
import java.util.concurrent.ConcurrentSkipListMap;

/**
 * 종목별 호가창 (Order Book)
 *
 * 자료구조:
 * - 매수 (BUY):  ConcurrentSkipListMap (내림차순) — 높은 가격 우선
 * - 매도 (SELL): ConcurrentSkipListMap (오름차순) — 낮은 가격 우선
 * - 각 가격 레벨: TreeSet<OrderBookEntry> (sequence 오름차순 — 시간 우선 FIFO)
 *
 * Thread-Safety: ConcurrentSkipListMap + synchronized per price level
 */
@Slf4j
public class OrderBook {

    private final String symbol;

    // 매수 호가: 높은 가격 → 낮은 가격 (내림차순)
    private final ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> bids =
            new ConcurrentSkipListMap<>(Comparator.reverseOrder());

    // 매도 호가: 낮은 가격 → 높은 가격 (오름차순)
    private final ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> asks =
            new ConcurrentSkipListMap<>();

    public OrderBook(String symbol) {
        this.symbol = symbol;
    }

    /**
     * 주문 추가
     */
    public void addOrder(OrderBookEntry entry) {
        ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> book =
                entry.getSide() == OrderSide.BUY ? bids : asks;
        book.computeIfAbsent(entry.getPrice(), k -> new TreeSet<>())
            .add(entry);
        log.debug("[OrderBook] 주문 등록 — symbol={}, side={}, price={}, qty={}",
                symbol, entry.getSide(), entry.getPrice(), entry.getRemainingQuantity());
    }

    /**
     * 주문 취소
     */
    public boolean cancelOrder(Long orderId, OrderSide side, BigDecimal price) {
        ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> book =
                side == OrderSide.BUY ? bids : asks;
        TreeSet<OrderBookEntry> level = book.get(price);
        if (level == null) return false;
        boolean removed = level.removeIf(e -> e.getOrderId().equals(orderId));
        if (level.isEmpty()) book.remove(price);
        return removed;
    }

    /**
     * 최우선 매수 호가 (Best Bid)
     */
    public Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestBid() {
        return bids.isEmpty() ? Optional.empty()
                              : Optional.of(bids.firstEntry());
    }

    /**
     * 최우선 매도 호가 (Best Ask)
     */
    public Optional<Map.Entry<BigDecimal, TreeSet<OrderBookEntry>>> bestAsk() {
        return asks.isEmpty() ? Optional.empty()
                              : Optional.of(asks.firstEntry());
    }

    /**
     * 가격 레벨별 매수/매도 호가 스냅샷 (상위 depth 개)
     */
    public OrderBookSnapshot getSnapshot(int depth) {
        List<PriceLevel> bidLevels = new ArrayList<>();
        List<PriceLevel> askLevels = new ArrayList<>();

        int count = 0;
        for (Map.Entry<BigDecimal, TreeSet<OrderBookEntry>> e : bids.entrySet()) {
            if (count++ >= depth) break;
            BigDecimal total = e.getValue().stream()
                    .map(OrderBookEntry::getRemainingQuantity)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            bidLevels.add(new PriceLevel(e.getKey(), total, e.getValue().size()));
        }

        count = 0;
        for (Map.Entry<BigDecimal, TreeSet<OrderBookEntry>> e : asks.entrySet()) {
            if (count++ >= depth) break;
            BigDecimal total = e.getValue().stream()
                    .map(OrderBookEntry::getRemainingQuantity)
                    .reduce(BigDecimal.ZERO, BigDecimal::add);
            askLevels.add(new PriceLevel(e.getKey(), total, e.getValue().size()));
        }

        return new OrderBookSnapshot(symbol, bidLevels, askLevels);
    }

    public void removePriceLevel(OrderSide side, BigDecimal price) {
        if (side == OrderSide.BUY) bids.remove(price);
        else asks.remove(price);
    }

    public ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> getBids() { return bids; }
    public ConcurrentSkipListMap<BigDecimal, TreeSet<OrderBookEntry>> getAsks() { return asks; }
    public String getSymbol() { return symbol; }

    // ── 내부 DTO ──────────────────────────────────────────────────
    public record PriceLevel(BigDecimal price, BigDecimal quantity, int orderCount) {}

    public record OrderBookSnapshot(String symbol,
                                    List<PriceLevel> bids,
                                    List<PriceLevel> asks) {}
}
