package com.exchange.settlement;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * T+2 정산, 세금 계산, 감독기관 리포팅
 * Port: 8085
 */
@SpringBootApplication
public class SettlementServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(SettlementServiceApplication.class, args);
    }
}
