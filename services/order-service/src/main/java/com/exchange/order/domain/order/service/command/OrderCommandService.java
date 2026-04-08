package com.exchange.order.domain.order.service.command;

import com.exchange.order.config.KafkaConfig;
import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.dto.OrderResponse;
import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.entity.OrderType;
import com.exchange.order.domain.order.event.OrderCreatedEvent;
import com.exchange.order.domain.order.event.OrderStatusChangedEvent;
import com.exchange.order.domain.order.port.OrderCommandPort;
import com.exchange.order.domain.order.port.OrderQueryPort;
import com.exchange.order.domain.order.strategy.OrderStrategy;
import com.exchange.order.domain.order.strategy.OrderStrategyFactory;
import com.exchange.order.domain.order.validator.OrderValidator;
import com.exchange.order.domain.outbox.service.OutboxService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.Map;

/**
 * [CQRS Command 측] 주문 생성/수정/삭제
 *
 * Outbox Pattern 통합:
 * - 주문 저장 + OutboxEvent 저장을 단일 @Transactional로 묶음
 * - Kafka 직접 발행 제거 → OutboxEventPublisher(스케줄러)가 담당
 * - 이중 쓰기 문제 완전 해소
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class OrderCommandService {

    private final OrderCommandPort orderCommandPort;
    private final OrderQueryPort orderQueryPort;
    private final OrderStrategyFactory strategyFactory;
    private final OrderValidator orderValidator;
    private final ApplicationEventPublisher eventPublisher;
    private final OutboxService outboxService;

    public OrderResponse createOrder(OrderRequest request) {
        // 1. 검증 체인
        orderValidator.validate(request);

        // 2. 전략 선택
        OrderType orderType = request.getOrderType() != null ? request.getOrderType() : OrderType.LIMIT;
        OrderStrategy strategy = strategyFactory.getStrategy(orderType);
        strategy.validate(request);
        strategy.preProcess(request);

        // 3. 주문 저장
        String side = (request.getSide() != null && !request.getSide().isBlank())
                ? request.getSide().toUpperCase() : "BUY";
        Order order = Order.builder()
                .customerName(request.getCustomerName())
                .productName(request.getProductName())
                .quantity(request.getQuantity())
                .totalPrice(request.getTotalPrice())
                .orderType(orderType)
                .side(side)
                .status(OrderStatus.PENDING)
                .build();
        Order savedOrder = orderCommandPort.save(order);

        // 4. Outbox 이벤트 저장 (같은 트랜잭션 — 원자성 보장)
        Map<String, Object> payload = Map.of(
            "orderId", savedOrder.getId(),
            "customerName", savedOrder.getCustomerName(),
            "productName", savedOrder.getProductName(),
            "quantity", savedOrder.getQuantity(),
            "totalPrice", savedOrder.getTotalPrice(),
            "orderType", savedOrder.getOrderType(),
            "side", savedOrder.getSide(),
            "status", savedOrder.getStatus()
        );
        outboxService.save("Order", savedOrder.getId(),
                "ORDER_CREATED", KafkaConfig.ORDER_TOPIC, payload);

        // 5. Spring 도메인 이벤트 (동기, 내부용)
        eventPublisher.publishEvent(new OrderCreatedEvent(this, savedOrder));
        strategy.postProcess(savedOrder.getId());

        log.info("[주문 생성] orderId={}, type={}", savedOrder.getId(), orderType);
        return OrderResponse.from(savedOrder);
    }

    @CacheEvict(value = "orders", key = "#id")
    public OrderResponse updateOrderStatus(Long id, OrderStatus newStatus) {
        Order order = orderQueryPort.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));

        OrderStatus previousStatus = order.getStatus();
        order.updateStatus(newStatus);
        Order updated = orderCommandPort.save(order);

        // Outbox: 상태 변경 이벤트
        outboxService.save("Order", id, "ORDER_STATUS_CHANGED",
                KafkaConfig.ORDER_STATUS_TOPIC,
                Map.of("orderId", id, "from", previousStatus, "to", newStatus));

        eventPublisher.publishEvent(
                new OrderStatusChangedEvent(this, id, previousStatus, newStatus));

        log.info("[상태 변경] orderId={}, {} → {}", id, previousStatus, newStatus);
        return OrderResponse.from(updated);
    }

    @CacheEvict(value = "orders", key = "#id")
    public void deleteOrder(Long id) {
        orderQueryPort.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
        orderCommandPort.deleteById(id);
        log.info("[주문 삭제] orderId={}", id);
    }
}
