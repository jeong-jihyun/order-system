package com.exchange.trading;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 주문 매칭 엔진 - Order Book, 체결 처리
 * Port: 8084
 */
@SpringBootApplication
public class TradingEngineApplication {
    public static void main(String[] args) {
        SpringApplication.run(TradingEngineApplication.class, args);
    }
}
