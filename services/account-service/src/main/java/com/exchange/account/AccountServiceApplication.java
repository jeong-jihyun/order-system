package com.exchange.account;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Account Service — 사용자 인증 + 계좌/잔고 관리
 * - Port: 8082
 * - JWT 발급/검증
 * - Spring Security (BCrypt 비밀번호)
 */
@SpringBootApplication
@EnableAsync
public class AccountServiceApplication {
    public static void main(String[] args) {
        SpringApplication.run(AccountServiceApplication.class, args);
    }
}
