package com.order.domain.order.service;

import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.dto.OrderResponse;
import com.order.domain.order.entity.Order;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.repository.OrderRepository;
import com.order.kafka.event.OrderEvent;
import com.order.kafka.producer.OrderEventProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderService {

    private final OrderRepository orderRepository;
    private final OrderEventProducer orderEventProducer;

    /**
     * 전체 주문 조회
     * [Week 1 Stream 실습] findAll() → stream().map(OrderResponse::from).collect(...)
     */
    public List<OrderResponse> getAllOrders() {
        return orderRepository.findAll().stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    /**
     * 단건 주문 조회
     * [Week 2 Redis 실습] @Cacheable — Redis에서 먼저 조회, 없으면 DB 조회 후 캐싱
     */
    @Cacheable(value = "orders", key = "#id")
    public OrderResponse getOrder(Long id) {
        log.debug("DB에서 주문 조회: id={}", id);
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
        return OrderResponse.from(order);
    }

    /**
     * 상태별 주문 조회
     * [Week 1 Stream 실습] filter / map 조합
     */
    public List<OrderResponse> getOrdersByStatus(OrderStatus status) {
        return orderRepository.findByStatus(status).stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    /**
     * PENDING 주문만 조회
     * [Week 1 Stream 실습] findAll() → stream().filter().map().collect()
     */
    public List<OrderResponse> getPendingOrders() {
        return orderRepository.findAll().stream()
                .filter(order -> order.getStatus() == OrderStatus.PENDING)
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    /**
     * 주문 생성
     * [Week 2 Kafka 실습] 저장 후 order-events 토픽으로 이벤트 발행
     */
    @Transactional
    public OrderResponse createOrder(OrderRequest request) {
        Order order = Order.builder()
                .customerName(request.getCustomerName())
                .productName(request.getProductName())
                .quantity(request.getQuantity())
                .totalPrice(request.getTotalPrice())
                .status(OrderStatus.PENDING)
                .build();

        Order savedOrder = orderRepository.save(order);

        // Kafka 이벤트 발행
        orderEventProducer.sendOrderEvent(OrderEvent.of(savedOrder));

        return OrderResponse.from(savedOrder);
    }

    /**
     * 주문 상태 변경
     * [Week 2 Redis 실습] @CacheEvict — 캐시 무효화로 데이터 일관성 유지
     */
    @Transactional
    @CacheEvict(value = "orders", key = "#id")
    public OrderResponse updateOrderStatus(Long id, OrderStatus status) {
        Order order = orderRepository.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
        order.updateStatus(status);
        // JPA 더티 체킹으로 명시적 save() 불필요
        return OrderResponse.from(order);
    }
}
