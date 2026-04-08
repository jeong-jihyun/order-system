package com.exchange.order.domain.order.port;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;

import java.util.List;
import java.util.Optional;

public interface OrderQueryPort {
    Optional<Order> findById(Long id);
    List<Order> findAll();
    List<Order> findByStatus(OrderStatus status);
    List<Order> findByCustomerName(String customerName);
}
