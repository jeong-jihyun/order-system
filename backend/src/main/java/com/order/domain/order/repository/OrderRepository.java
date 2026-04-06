package com.order.domain.order.repository;

import com.order.domain.order.entity.Order;
import com.order.domain.order.entity.OrderStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrderRepository extends JpaRepository<Order, Long> {

    /** [Week 1 Stream 실습] 상태별 조회 후 Stream 변환 연습 */
    List<Order> findByStatus(OrderStatus status);

    /** 고객명으로 조회 */
    List<Order> findByCustomerNameContaining(String customerName);
}
