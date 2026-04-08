package com.order.domain.order.port;

import com.order.domain.order.entity.Order;
import com.order.domain.order.entity.OrderStatus;

import java.util.List;
import java.util.Optional;

/**
 * [DIP + ISP] 읽기 전용 포트 인터페이스
 * - 고수준 모듈(QueryService)이 저수준 구현(JPA Repository)에 직접 의존하지 않음
 * - Hexagonal Architecture의 Secondary Port (Driven Port)
 * - 테스트 시 Mock 구현체로 쉽게 교체 가능
 */
public interface OrderQueryPort {
    Optional<Order> findById(Long id);
    List<Order> findAll();
    List<Order> findByStatus(OrderStatus status);
    List<Order> findByCustomerName(String customerName);
}
