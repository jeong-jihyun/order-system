package com.exchange.order.infrastructure.client;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

import java.math.BigDecimal;
import java.util.Map;

/**
 * account-service REST 클라이언트
 * 주문 생성/취소 시 증거금 동결/해제 요청
 */
@Slf4j
@Component
public class AccountServiceClient {

    private final RestTemplate restTemplate;
    private final String accountServiceUrl;

    public AccountServiceClient(
            @Value("${order.account-service-url:http://exchange-account-service:8082}") String url) {
        this.restTemplate = new RestTemplate();
        this.accountServiceUrl = url;
    }

    /**
     * 주문 접수 시 증거금 동결
     * @return true=동결 성공, false=잔고 부족 등 실패
     */
    public boolean freezeBalance(String username, BigDecimal amount) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            Map<String, Object> body = Map.of("username", username, "amount", amount);
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);

            ResponseEntity<String> response = restTemplate.exchange(
                    accountServiceUrl + "/api/v1/accounts/freeze",
                    HttpMethod.POST, request, String.class);
            log.info("[증거금 동결] user={}, amount={}, status={}", username, amount, response.getStatusCode());
            return response.getStatusCode().is2xxSuccessful();
        } catch (Exception e) {
            log.warn("[증거금 동결 실패] user={}, amount={}, error={}", username, amount, e.getMessage());
            return false;
        }
    }

    /**
     * 주문 취소 시 증거금 해제
     */
    public void unfreezeBalance(String username, BigDecimal amount) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            Map<String, Object> body = Map.of("username", username, "amount", amount);
            HttpEntity<Map<String, Object>> request = new HttpEntity<>(body, headers);

            restTemplate.exchange(
                    accountServiceUrl + "/api/v1/accounts/unfreeze",
                    HttpMethod.POST, request, String.class);
            log.info("[증거금 해제] user={}, amount={}", username, amount);
        } catch (Exception e) {
            log.warn("[증거금 해제 실패] user={}, amount={}, error={}", username, amount, e.getMessage());
        }
    }
}
