package com.exchange.trading.domain.orderbook.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.concurrent.ConcurrentHashMap;

/**
 * 종목별 OrderBook 인스턴스 관리
 * ConcurrentHashMap: 종목 추가/조회 Thread-Safe
 */
@Slf4j
@Component
public class OrderBookRegistry {

    private final ConcurrentHashMap<String, OrderBook> orderBooks = new ConcurrentHashMap<>();

    public OrderBook getOrCreate(String symbol) {
        return orderBooks.computeIfAbsent(symbol, s -> {
            log.info("[OrderBook] 신규 종목 호가창 생성 — symbol={}", s);
            return new OrderBook(s);
        });
    }

    public OrderBook get(String symbol) {
        OrderBook ob = orderBooks.get(symbol);
        if (ob == null) throw new IllegalArgumentException("호가창이 없습니다: " + symbol);
        return ob;
    }

    public boolean exists(String symbol) { return orderBooks.containsKey(symbol); }
}
