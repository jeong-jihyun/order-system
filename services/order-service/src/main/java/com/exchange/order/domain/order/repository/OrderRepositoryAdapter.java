package com.exchange.order.domain.order.repository;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.port.OrderCommandPort;
import com.exchange.order.domain.order.port.OrderQueryPort;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Optional;

/**
 * Hexagonal Architecture — Repository Adapter
 * DIP: 서비스는 Port 인터페이스에만 의존, 구현체(JPA)는 여기에만 위치
 */
@Component
@RequiredArgsConstructor
public class OrderRepositoryAdapter implements OrderQueryPort, OrderCommandPort {

    private final OrderRepository orderRepository;

    @Override public Optional<Order> findById(Long id)            { return orderRepository.findById(id); }
    @Override public List<Order> findAll()                        { return orderRepository.findAll(); }
    @Override public List<Order> findByStatus(OrderStatus status) { return orderRepository.findByStatus(status); }
    @Override public List<Order> findByCustomerName(String name)  { return orderRepository.findByCustomerName(name); }
    @Override public Order save(Order order)                      { return orderRepository.save(order); }
    @Override public void deleteById(Long id)                     { orderRepository.deleteById(id); }
}
