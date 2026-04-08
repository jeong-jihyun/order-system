package com.exchange.gateway.controller;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

import java.util.Map;

/**
 * Circuit Breaker Fallback — 하위 서비스 장애 시 기본 응답 반환
 */
@RestController
public class FallbackController {

    @RequestMapping("/fallback")
    public Mono<Map<String, Object>> fallback(ServerWebExchange exchange) {
        exchange.getResponse().setStatusCode(HttpStatus.SERVICE_UNAVAILABLE);
        return Mono.just(Map.of(
                "success", false,
                "message", "서비스가 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
                "status", 503
        ));
    }
}
