package com.exchange.order.domain.order.service.command;

import com.exchange.order.config.KafkaConfig;
import com.exchange.order.domain.order.dto.OrderRequest;
import com.exchange.order.domain.order.dto.OrderResponse;
import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderSide;
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
import com.exchange.order.infrastructure.client.AccountServiceClient;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.HashMap;
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
    private final AccountServiceClient accountServiceClient;

    public OrderResponse createOrder(OrderRequest request) {
        // 1. 검증 체인
        orderValidator.validate(request);

        // 2. 전략 선택
        OrderType orderType = request.getOrderType() != null ? request.getOrderType() : OrderType.LIMIT;
        OrderStrategy strategy = strategyFactory.getStrategy(orderType);
        strategy.validate(request);
        strategy.preProcess(request);

        // 3. side 결정
        String sideStr = (request.getSide() != null && !request.getSide().isBlank())
                ? request.getSide().toUpperCase() : "BUY";
        OrderSide side = OrderSide.valueOf(sideStr);

        // 4. 매수 주문 시 증거금 동결 (account-service 호출)
        BigDecimal orderAmount = request.getTotalPrice()
                .multiply(request.getQuantity());
        if (OrderSide.BUY == side) {
            boolean frozen = accountServiceClient.freezeBalance(request.getCustomerName(), orderAmount);
            if (!frozen) {
                throw new IllegalStateException("잔고가 부족합니다. 증거금 동결 실패.");
            }
        }

        // 5. 주문 저장
        Order order = Order.builder()
                .customerName(request.getCustomerName())
                .productName(request.getProductName())
                .quantity(request.getQuantity())
                .totalPrice(request.getTotalPrice())
                .orderType(orderType)
                .side(side)
                .stopPrice(request.getStopPrice())
                .status(OrderStatus.PENDING)
                .build();
        Order savedOrder = orderCommandPort.save(order);

        // 4. Outbox 이벤트 저장 (같은 트랜잭션 — 원자성 보장)
        HashMap<String, Object> payload = new HashMap<>();
        payload.put("orderId", savedOrder.getId());
        payload.put("customerName", savedOrder.getCustomerName());
        payload.put("productName", savedOrder.getProductName());
        payload.put("quantity", savedOrder.getQuantity());
        payload.put("totalPrice", savedOrder.getTotalPrice());
        payload.put("orderType", savedOrder.getOrderType());
        payload.put("side", savedOrder.getSide());
        payload.put("status", savedOrder.getStatus());
        if (savedOrder.getStopPrice() != null) {
            payload.put("stopPrice", savedOrder.getStopPrice());
        }
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

        // 취소 시 BUY 주문의 증거금 해제
        if (newStatus == OrderStatus.CANCELLED && OrderSide.BUY == order.getSide()) {
            BigDecimal orderAmount = order.getTotalPrice()
                    .multiply(order.getQuantity());
            accountServiceClient.unfreezeBalance(order.getCustomerName(), orderAmount);
        }

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
