package com.exchange.gateway;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * API Gateway — 모든 클라이언트 요청의 단일 진입점
 * - Port: 8080
 * - Spring Cloud Gateway (Reactive/WebFlux)
 * - JWT 인증, Rate Limiting, Circuit Breaker
 */
@SpringBootApplication
public class ApiGatewayApplication {
    public static void main(String[] args) {
        SpringApplication.run(ApiGatewayApplication.class, args);
    }
}
