package com.order.domain.order.service.query;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.order.domain.order.dto.OrderResponse;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.port.OrderQueryPort;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.data.redis.core.RedisTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * [SRP] 주문 Query(읽기) 전용 서비스 - CQRS Query 측
 *
 * SOLID:
 * - SRP: 조회 로직만 담당
 * - DIP: OrderQueryPort (인터페이스)에만 의존
 *
 * 패턴:
 * - CQRS: Command와 Query 완전 분리
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderQueryService {

    private final OrderQueryPort orderQueryPort;
    private final RedisTemplate<String, String> redisTemplate;
    private final ObjectMapper objectMapper;
    
    public List<OrderResponse> getAllOrders() {
        return orderQueryPort.findAll().stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    @Cacheable(value = "orders", key = "#id")
    public OrderResponse getOrder(Long id) {
        log.debug("[캐시 미스] DB 조회 orderId={}", id);
        return orderQueryPort.findById(id)
                .map(OrderResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
    }

    public List<OrderResponse> getOrdersByStatus(OrderStatus status) {
        return orderQueryPort.findByStatus(status).stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    public List<OrderResponse> getPendingOrders() {
        return orderQueryPort.findByStatus(OrderStatus.PENDING).stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    /** [Stream 심화] 전체 주문 총 금액 합산 */
    public BigDecimal getOrdersTotalAmount() {
        return orderQueryPort.findAll().stream()
                .map(order -> order.getTotalPrice())
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /** [Stream 심화] 상태별 주문 건수 집계 */
    public Map<OrderStatus, Long> getOrderCountByStatus() {
        return orderQueryPort.findAll().stream()
                .collect(Collectors.groupingBy(
                        order -> order.getStatus(),
                        Collectors.counting()));
    }

    /** [Stream 심화] PENDING 주문 금액 내림차순 정렬 */
    public List<OrderResponse> getPendingOrdersSortedByPrice() {
        return orderQueryPort.findByStatus(OrderStatus.PENDING).stream()
                .sorted((a, b) -> b.getTotalPrice().compareTo(a.getTotalPrice()))
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    public OrderResponse getOrderManual(Long id) {
        String cacheKey = "orders::" + id;

        // 1단계: Redis에서 캐시 확인
        String cached = redisTemplate.opsForValue().get(cacheKey);
        if (cached != null) {
            // 2단계: 캐시 히트 → JSON 문자열을 OrderResponse 객체로 역직렬화
            try {
                return objectMapper.readValue(cached, OrderResponse.class);
            } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
                log.warn("[캐시 역직렬화 실패] key={}, 이유={}", cacheKey, e.getMessage());
                // 역직렬화 실패 시 캐시 무시하고 DB 조회로 fall-through
            }
        }

        // 3단계: 캐시 미스 → DB 조회
        OrderResponse response = orderQueryPort.findById(id)
                .map(OrderResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다."));

        // 4단계: Java 객체 → JSON 문자열로 직렬화 후 Redis에 저장 (TTL 5분)
        try {
            String json = objectMapper.writeValueAsString(response);
            redisTemplate.opsForValue().set(cacheKey, json, Duration.ofMinutes(5));
        } catch (com.fasterxml.jackson.core.JsonProcessingException e) {
            log.warn("[캐시 저장 실패] key={}, 이유={}", cacheKey, e.getMessage());
            // 직렬화 실패 시 캐시 저장 생략, 조회 결과는 정상 반환
        }

        return response;
    }
}
