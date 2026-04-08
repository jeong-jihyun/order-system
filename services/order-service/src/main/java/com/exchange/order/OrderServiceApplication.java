package com.exchange.order;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Order Service — 마이크로서비스 독립 실행 진입점
 * - Port: 8081
 * - Outbox Pattern으로 Kafka 발행 신뢰성 보장
 */
@SpringBootApplication
@EnableAsync
@EnableScheduling
public class OrderServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(OrderServiceApplication.class, args);
    }
}
