package com.exchange.order.domain.order.service.query;

import com.exchange.order.domain.order.dto.OrderResponse;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.port.OrderQueryPort;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * [CQRS Query 측] 주문 조회 전용 — @Cacheable Redis 캐싱 적용
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderQueryService {

    private final OrderQueryPort orderQueryPort;

    @Cacheable(value = "orders", key = "#id")
    public OrderResponse getOrder(Long id) {
        return orderQueryPort.findById(id)
                .map(OrderResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
    }

    public List<OrderResponse> getAllOrders() {
        return orderQueryPort.findAll().stream()
                .map(OrderResponse::from)
                .toList();
    }

    public List<OrderResponse> getOrdersByStatus(OrderStatus status) {
        return orderQueryPort.findByStatus(status).stream()
                .map(OrderResponse::from)
                .toList();
    }

    public List<OrderResponse> getOrdersByCustomer(String customerName) {
        return orderQueryPort.findByCustomerName(customerName).stream()
                .map(OrderResponse::from)
                .toList();
    }

    /** 상태별 집계 통계 */
    public Map<OrderStatus, Long> getOrderStatsByStatus() {
        return orderQueryPort.findAll().stream()
                .collect(Collectors.groupingBy(
                        o -> o.getStatus(),
                        Collectors.counting()));
    }
}
