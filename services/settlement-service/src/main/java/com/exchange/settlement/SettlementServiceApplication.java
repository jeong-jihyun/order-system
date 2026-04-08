package com.exchange.settlement;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;
import org.springframework.scheduling.annotation.EnableScheduling;

/**
 * Settlement Service — T+2 정산 서비스
 * Port: 8085
 * - 체결 이벤트 수신 → 정산 레코드 생성
 * - 수수료(0.015%) + 거래세(매도 0.2%) 계산
 * - T+2 스케줄러 → 잔고 반영 이벤트 발행
 */
@SpringBootApplication
@EnableAsync
@EnableScheduling
public class SettlementServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(SettlementServiceApplication.class, args);
    }
}
