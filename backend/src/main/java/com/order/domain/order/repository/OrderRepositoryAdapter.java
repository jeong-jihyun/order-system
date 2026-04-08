package com.order.domain.order.repository;

import com.order.domain.order.entity.Order;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.port.OrderCommandPort;
import com.order.domain.order.port.OrderQueryPort;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

/**
 * [DIP] Port 인터페이스의 구현체 - JPA Repository 어댑터
 * OrderQueryPort + OrderCommandPort 구현
 * Hexagonal Architecture의 Secondary Adapter
 */
@Repository
@RequiredArgsConstructor
public class OrderRepositoryAdapter implements OrderQueryPort, OrderCommandPort {

    private final OrderRepository orderRepository;

    @Override
    public Optional<Order> findById(Long id) {
        return orderRepository.findById(id);
    }

    @Override
    public List<Order> findAll() {
        return orderRepository.findAll();
    }

    @Override
    public List<Order> findByStatus(OrderStatus status) {
        return orderRepository.findByStatus(status);
    }

    @Override
    public List<Order> findByCustomerName(String customerName) {
        return orderRepository.findByCustomerNameContaining(customerName);
    }

    @Override
    public Order save(Order order) {
        return orderRepository.save(order);
    }

    @Override
    public void deleteById(Long id) {
        orderRepository.deleteById(id);
    }
}
