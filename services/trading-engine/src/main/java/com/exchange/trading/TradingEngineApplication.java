package com.exchange.trading;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Trading Engine — Price-Time Priority 주문 매칭 엔진
 * Port: 8084
 * - Order Book: ConcurrentSkipListMap 기반 (자동 가격 정렬)
 * - Matching: 가격 우선 → 시간 우선 (FIFO per price level)
 * - Kafka Consumer: 신규 주문 수신
 * - Kafka Producer: 체결 결과 발행
 */
@SpringBootApplication
@EnableAsync
public class TradingEngineApplication {
    public static void main(String[] args) {
        SpringApplication.run(TradingEngineApplication.class, args);
    }
}
