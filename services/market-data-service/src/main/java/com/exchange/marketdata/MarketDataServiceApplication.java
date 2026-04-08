package com.exchange.marketdata;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Market Data Service — 실시간 시세/OHLCV 브로드캐스팅
 * Port: 8083
 * - STOMP WebSocket: /ws (클라이언트 ↔ 서버 양방향)
 * - Redis Pub/Sub: 멀티 인스턴스 간 시세 동기화
 * - Kafka Consumer: 체결 이벤트 → 시세 업데이트
 */
@SpringBootApplication
@EnableScheduling
public class MarketDataServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(MarketDataServiceApplication.class, args);
    }
}
