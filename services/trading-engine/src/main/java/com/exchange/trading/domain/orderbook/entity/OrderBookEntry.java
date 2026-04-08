package com.exchange.trading.domain.orderbook.entity;

import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 호가창에 보관되는 주문 항목
 * - price: 지정가 (MARKET 주문은 null)
 * - sequence: 동일 가격 내 시간 우선을 위한 단조 증가 시퀀스
 */
@Getter
@Builder
public class OrderBookEntry implements Comparable<OrderBookEntry> {

    private static final AtomicLong SEQUENCE = new AtomicLong(0);

    private final Long orderId;
    private final String symbol;
    private final OrderSide side;
    private final BigDecimal price;     // null이면 MARKET 주문
    private final BigDecimal originalQuantity;
    private volatile BigDecimal remainingQuantity;
    private final String customerName;  // 주문자 username (정산 연동용)
    private final LocalDateTime createdAt;
    private final long sequence;        // 시간 우선 정렬용

    public static OrderBookEntry create(Long orderId, String symbol, OrderSide side,
                                        BigDecimal price, BigDecimal quantity,
                                        String customerName) {
        return OrderBookEntry.builder()
                .orderId(orderId)
                .symbol(symbol)
                .side(side)
                .price(price)
                .originalQuantity(quantity)
                .remainingQuantity(quantity)
                .customerName(customerName)
                .createdAt(LocalDateTime.now())
                .sequence(SEQUENCE.incrementAndGet())
                .build();
    }

    public void fill(BigDecimal filledQuantity) {
        this.remainingQuantity = this.remainingQuantity.subtract(filledQuantity);
    }

    public boolean isFilled() {
        return remainingQuantity.compareTo(BigDecimal.ZERO) <= 0;
    }

    /**
     * 동일 가격 내 시간 우선 (sequence 오름차순)
     */
    @Override
    public int compareTo(OrderBookEntry other) {
        return Long.compare(this.sequence, other.sequence);
    }
}
