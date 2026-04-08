package com.exchange.order.domain.order.repository;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface OrderRepository extends JpaRepository<Order, Long> {
    List<Order> findByStatus(OrderStatus status);
    List<Order> findByCustomerName(String customerName);
}
