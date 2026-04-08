package com.order.domain.order.service.command;

import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.dto.OrderResponse;
import com.order.domain.order.entity.Order;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.entity.OrderType;
import com.order.domain.order.event.OrderCreatedEvent;
import com.order.domain.order.event.OrderStatusChangedEvent;
import com.order.domain.order.port.OrderCommandPort;
import com.order.domain.order.port.OrderQueryPort;
import com.order.domain.order.strategy.OrderStrategy;
import com.order.domain.order.strategy.OrderStrategyFactory;
import com.order.domain.order.validator.OrderValidator;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.context.ApplicationEventPublisher;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * [SRP] 주문 Command(쓰기) 전용 서비스 - CQRS Command 측
 *
 * 적용 패턴:
 * - Strategy: 주문 타입별 처리를 OrderStrategyFactory로 위임
 * - Factory: OrderStrategyFactory가 전략 선택 담당
 * - Observer: 비즈니스 이벤트 발행 (Kafka 발행은 리스너가 처리)
 * - Chain of Responsibility: OrderValidator 체인으로 유효성 검사
 *
 * SOLID:
 * - SRP: Command 로직만 담당 (조회는 OrderQueryService)
 * - OCP: 새 주문 타입은 Strategy 추가로만 대응
 * - DIP: OrderCommandPort/QueryPort 인터페이스에만 의존
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

    /**
     * 주문 생성
     * 1. Chain of Responsibility로 검증
     * 2. Strategy로 실행 가격 계산
     * 3. 저장
     * 4. 도메인 이벤트 발행 (Kafka 발행은 EventListener가 처리)
     */
    public OrderResponse createOrder(OrderRequest request) {
        // 1. 검증 체인 실행
        orderValidator.validate(request);

        // 2. 주문 타입 결정 (기본값: LIMIT)
        OrderType orderType = request.getOrderType() != null ? request.getOrderType() : OrderType.LIMIT;
        OrderStrategy strategy = strategyFactory.getStrategy(orderType);
        strategy.validate(request);

        // 3. 주문 생성 및 저장
        Order order = Order.builder()
                .customerName(request.getCustomerName())
                .productName(request.getProductName())
                .quantity(request.getQuantity())
                .totalPrice(request.getTotalPrice())
                .orderType(orderType)
                .status(OrderStatus.PENDING)
                .build();

        Order savedOrder = orderCommandPort.save(order);
        log.info("[주문 생성] orderId={}, type={}", savedOrder.getId(), orderType);

        // 4. 도메인 이벤트 발행 (Observer - 리스너가 Kafka 발행 담당)
        eventPublisher.publishEvent(new OrderCreatedEvent(this, savedOrder));

        return OrderResponse.from(savedOrder);
    }

    /**
     * 주문 상태 변경
     * State Machine 검증 포함 (OrderStatus.canTransitionTo)
     */
    @CacheEvict(value = "orders", key = "#id")
    public OrderResponse updateOrderStatus(Long id, OrderStatus newStatus) {
        Order order = orderQueryPort.findById(id)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));

        OrderStatus previousStatus = order.getStatus();
        order.updateStatus(newStatus); // State Machine 검증 포함
        orderCommandPort.save(order);

        log.info("[상태 변경] orderId={}, {} -> {}", id, previousStatus, newStatus);

        // 상태 변경 이벤트 발행
        eventPublisher.publishEvent(new OrderStatusChangedEvent(this, id, previousStatus, newStatus));

        return OrderResponse.from(order);
    }
}
