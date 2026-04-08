#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 0: SOLID + Design Pattern 리팩토링 파일 일괄 생성"""

import os

BASE = r"d:\order-system\backend\src\main\java\com\order"

files = {}

# ──────────────────────────────────────────────
# 1. OrderType enum
# ──────────────────────────────────────────────
files["domain/order/entity/OrderType.java"] = """package com.order.domain.order.entity;

/**
 * 주문 타입 - Strategy 패턴의 타입 식별자
 * OCP: 새 주문 타입 추가 시 이 enum과 새 Strategy 클래스만 추가
 */
public enum OrderType {
    MARKET,       // 시장가 주문 - 즉시 체결, 가격 지정 불가
    LIMIT,        // 지정가 주문 - 지정 가격 이하에서만 체결
    STOP_LOSS,    // 손절 주문 - 특정 가격 하락 시 자동 매도
    STOP_LIMIT    // 스톱리밋 - 스톱 가격 도달 시 지정가 주문 전환
}
"""

# ──────────────────────────────────────────────
# 2. OrderStatus (State Machine 패턴)
# ──────────────────────────────────────────────
files["domain/order/entity/OrderStatus.java"] = """package com.order.domain.order.entity;

/**
 * 주문 상태 - State Machine 패턴
 * canTransitionTo()로 허용된 전이만 가능하도록 강제
 */
public enum OrderStatus {
    PENDING,     // 주문 대기
    PROCESSING,  // 처리 중
    COMPLETED,   // 완료
    CANCELLED;   // 취소

    /** 최종 상태 여부 (이후 전이 불가) */
    public boolean isTerminal() {
        return this == COMPLETED || this == CANCELLED;
    }

    /**
     * 상태 전이 유효성 검사
     * PENDING    -> PROCESSING | CANCELLED
     * PROCESSING -> COMPLETED  | CANCELLED
     */
    public boolean canTransitionTo(OrderStatus next) {
        return switch (this) {
            case PENDING    -> next == PROCESSING || next == CANCELLED;
            case PROCESSING -> next == COMPLETED  || next == CANCELLED;
            case COMPLETED, CANCELLED -> false;
        };
    }
}
"""

# ──────────────────────────────────────────────
# 3. Order Entity (OrderType 필드 추가)
# ──────────────────────────────────────────────
files["domain/order/entity/Order.java"] = """package com.order.domain.order.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.LocalDateTime;

/**
 * 주문 엔티티
 * - OrderType 필드 추가 (Phase 0)
 * - updateStatus()에 State Machine 검증 적용
 */
@Entity
@Table(name = "orders")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@AllArgsConstructor
@Builder
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 50)
    private String customerName;

    @Column(nullable = false, length = 100)
    private String productName;

    @Column(nullable = false)
    private Integer quantity;

    @Column(nullable = false, precision = 12, scale = 2)
    private BigDecimal totalPrice;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private OrderType orderType = OrderType.LIMIT;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    private OrderStatus status;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    @UpdateTimestamp
    private LocalDateTime updatedAt;

    /**
     * 상태 변경 - State Machine 패턴으로 유효하지 않은 전이 차단
     */
    public void updateStatus(OrderStatus newStatus) {
        if (!this.status.canTransitionTo(newStatus)) {
            throw new IllegalStateException(
                String.format("'%s' 상태에서 '%s'로 전이할 수 없습니다.", this.status, newStatus)
            );
        }
        this.status = newStatus;
    }
}
"""

# ──────────────────────────────────────────────
# 4. Strategy 인터페이스 (Strategy Pattern + ISP)
# ──────────────────────────────────────────────
files["domain/order/strategy/OrderStrategy.java"] = """package com.order.domain.order.strategy;

import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.entity.OrderType;
import java.math.BigDecimal;

/**
 * [Strategy Pattern + ISP]
 * - OCP: 새 주문 타입 추가 시 이 인터페이스를 구현하는 클래스만 추가
 * - ISP: default 메서드로 공통 기본 동작 제공, 타입별 Override
 */
public interface OrderStrategy {
    /** 이 전략이 처리하는 주문 타입 */
    OrderType getOrderType();

    /** 주문 실행 가격 계산 */
    BigDecimal calculateExecutionPrice(BigDecimal requestedPrice, BigDecimal marketPrice);

    /** 즉시 체결 가능 여부 */
    boolean isImmediateExecution();

    /** 기본 유효성 검사 - Override 가능 */
    default void validate(OrderRequest request) {
        if (request.getQuantity() == null || request.getQuantity() <= 0) {
            throw new IllegalArgumentException("수량은 1 이상이어야 합니다.");
        }
    }
}
"""

# ──────────────────────────────────────────────
# 5. MarketOrderStrategy
# ──────────────────────────────────────────────
files["domain/order/strategy/MarketOrderStrategy.java"] = """package com.order.domain.order.strategy;

import com.order.domain.order.entity.OrderType;
import org.springframework.stereotype.Component;
import java.math.BigDecimal;

/**
 * [Strategy Pattern] 시장가 주문
 * - 즉시 체결, 현재 시장가로 실행
 */
@Component
public class MarketOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getOrderType() { return OrderType.MARKET; }

    @Override
    public BigDecimal calculateExecutionPrice(BigDecimal requestedPrice, BigDecimal marketPrice) {
        return marketPrice; // 시장가 = 현재가
    }

    @Override
    public boolean isImmediateExecution() { return true; }
}
"""

# ──────────────────────────────────────────────
# 6. LimitOrderStrategy
# ──────────────────────────────────────────────
files["domain/order/strategy/LimitOrderStrategy.java"] = """package com.order.domain.order.strategy;

import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.entity.OrderType;
import org.springframework.stereotype.Component;
import java.math.BigDecimal;

/**
 * [Strategy Pattern] 지정가 주문
 * - 지정 가격 이하일 때만 체결 (즉시 체결 불가)
 */
@Component
public class LimitOrderStrategy implements OrderStrategy {

    @Override
    public OrderType getOrderType() { return OrderType.LIMIT; }

    @Override
    public BigDecimal calculateExecutionPrice(BigDecimal requestedPrice, BigDecimal marketPrice) {
        return requestedPrice; // 지정가 그대로
    }

    @Override
    public boolean isImmediateExecution() { return false; }

    @Override
    public void validate(OrderRequest request) {
        OrderStrategy.super.validate(request);
        if (request.getTotalPrice() == null || request.getTotalPrice().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("지정가 주문은 가격을 반드시 지정해야 합니다.");
        }
    }
}
"""

# ──────────────────────────────────────────────
# 7. OrderStrategyFactory (Factory Pattern)
# ──────────────────────────────────────────────
files["domain/order/strategy/OrderStrategyFactory.java"] = """package com.order.domain.order.strategy;

import com.order.domain.order.entity.OrderType;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * [Factory Pattern]
 * Spring이 주입한 모든 OrderStrategy 구현체를 Map으로 관리.
 * OCP: 새 Strategy 추가 시 Factory 코드 수정 불필요 - 자동 등록됨
 * DIP: 고수준(OrderCommandService)이 저수준(구체 전략)에 직접 의존하지 않음
 */
@Component
@RequiredArgsConstructor
public class OrderStrategyFactory {

    private final Map<OrderType, OrderStrategy> strategyMap;

    public OrderStrategyFactory(List<OrderStrategy> strategies) {
        this.strategyMap = strategies.stream()
            .collect(Collectors.toMap(OrderStrategy::getOrderType, Function.identity()));
    }

    public OrderStrategy getStrategy(OrderType orderType) {
        OrderStrategy strategy = strategyMap.get(orderType);
        if (strategy == null) {
            throw new IllegalArgumentException("지원하지 않는 주문 타입입니다: " + orderType);
        }
        return strategy;
    }
}
"""

# ──────────────────────────────────────────────
# 8. Port 인터페이스 (DIP - Hexagonal Architecture 준비)
# ──────────────────────────────────────────────
files["domain/order/port/OrderQueryPort.java"] = """package com.order.domain.order.port;

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
"""

files["domain/order/port/OrderCommandPort.java"] = """package com.order.domain.order.port;

import com.order.domain.order.entity.Order;

/**
 * [DIP + ISP] 쓰기 전용 포트 인터페이스
 * - ISP: 읽기/쓰기를 분리함으로써 불필요한 의존 방지
 * - CQRS 패턴으로의 자연스러운 전환 지원
 */
public interface OrderCommandPort {
    Order save(Order order);
    void deleteById(Long id);
}
"""

# ──────────────────────────────────────────────
# 9. Repository 어댑터 (Port 구현체)
# ──────────────────────────────────────────────
files["domain/order/repository/OrderRepositoryAdapter.java"] = """package com.order.domain.order.repository;

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
"""

# ──────────────────────────────────────────────
# 10. 도메인 이벤트 (Domain Event Pattern)
# ──────────────────────────────────────────────
files["domain/order/event/OrderCreatedEvent.java"] = """package com.order.domain.order.event;

import com.order.domain.order.entity.Order;
import lombok.Getter;
import org.springframework.context.ApplicationEvent;

import java.time.LocalDateTime;

/**
 * [Observer Pattern - Spring ApplicationEvent]
 * 주문 생성 도메인 이벤트.
 * OrderCommandService는 이벤트만 발행 -> Kafka 발행은 리스너가 담당
 * SRP: 서비스는 비즈니스 로직만, 인프라 관심사는 리스너로 분리
 */
@Getter
public class OrderCreatedEvent extends ApplicationEvent {

    private final Long orderId;
    private final String customerName;
    private final String productName;
    private final LocalDateTime occurredAt;

    public OrderCreatedEvent(Object source, Order order) {
        super(source);
        this.orderId = order.getId();
        this.customerName = order.getCustomerName();
        this.productName = order.getProductName();
        this.occurredAt = LocalDateTime.now();
    }
}
"""

files["domain/order/event/OrderStatusChangedEvent.java"] = """package com.order.domain.order.event;

import com.order.domain.order.entity.OrderStatus;
import lombok.Getter;
import org.springframework.context.ApplicationEvent;

import java.time.LocalDateTime;

/**
 * [Observer Pattern] 주문 상태 변경 도메인 이벤트
 */
@Getter
public class OrderStatusChangedEvent extends ApplicationEvent {

    private final Long orderId;
    private final OrderStatus previousStatus;
    private final OrderStatus newStatus;
    private final LocalDateTime occurredAt;

    public OrderStatusChangedEvent(Object source, Long orderId,
                                   OrderStatus previousStatus, OrderStatus newStatus) {
        super(source);
        this.orderId = orderId;
        this.previousStatus = previousStatus;
        this.newStatus = newStatus;
        this.occurredAt = LocalDateTime.now();
    }
}
"""

# ──────────────────────────────────────────────
# 11. OrderValidator (Chain of Responsibility)
# ──────────────────────────────────────────────
files["domain/order/validator/OrderValidator.java"] = """package com.order.domain.order.validator;

import com.order.domain.order.dto.OrderRequest;

/**
 * [Chain of Responsibility Pattern]
 * 주문 검증 체인의 기본 인터페이스.
 * 각 검증기는 자신의 검증 후 다음 검증기로 forwarding.
 * OCP: 새 검증 규칙 추가 시 새 Validator 클래스와 체인 연결만 추가
 */
public interface OrderValidator {
    void validate(OrderRequest request);
    
    /** 다음 검증기 설정 후 this 반환 (Fluent API) */
    default OrderValidator andThen(OrderValidator next) {
        return request -> {
            this.validate(request);
            next.validate(request);
        };
    }
}
"""

files["domain/order/validator/QuantityValidator.java"] = """package com.order.domain.order.validator;

import com.order.domain.order.dto.OrderRequest;
import org.springframework.stereotype.Component;

/**
 * [Chain of Responsibility] 수량 검증기
 */
@Component
public class QuantityValidator implements OrderValidator {
    private static final int MAX_QUANTITY = 10_000;

    @Override
    public void validate(OrderRequest request) {
        if (request.getQuantity() == null || request.getQuantity() <= 0) {
            throw new IllegalArgumentException("수량은 1 이상이어야 합니다.");
        }
        if (request.getQuantity() > MAX_QUANTITY) {
            throw new IllegalArgumentException("단일 주문 최대 수량은 " + MAX_QUANTITY + "개입니다.");
        }
    }
}
"""

files["domain/order/validator/PriceValidator.java"] = """package com.order.domain.order.validator;

import com.order.domain.order.dto.OrderRequest;
import org.springframework.stereotype.Component;

import java.math.BigDecimal;

/**
 * [Chain of Responsibility] 가격 검증기
 */
@Component
public class PriceValidator implements OrderValidator {
    private static final BigDecimal MAX_PRICE = new BigDecimal("1000000000"); // 10억

    @Override
    public void validate(OrderRequest request) {
        if (request.getTotalPrice() == null || request.getTotalPrice().compareTo(BigDecimal.ZERO) <= 0) {
            throw new IllegalArgumentException("주문 금액은 0보다 커야 합니다.");
        }
        if (request.getTotalPrice().compareTo(MAX_PRICE) > 0) {
            throw new IllegalArgumentException("단일 주문 최대 금액은 10억원입니다.");
        }
    }
}
"""

# ──────────────────────────────────────────────
# 12. OrderCommandService (SRP - 쓰기 전용)
# ──────────────────────────────────────────────
files["domain/order/service/command/OrderCommandService.java"] = """package com.order.domain.order.service.command;

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
"""

# ──────────────────────────────────────────────
# 13. OrderQueryService (SRP - 읽기 전용, CQRS Query 측)
# ──────────────────────────────────────────────
files["domain/order/service/query/OrderQueryService.java"] = """package com.order.domain.order.service.query;

import com.order.domain.order.dto.OrderResponse;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.port.OrderQueryPort;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * [SRP] 주문 Query(읽기) 전용 서비스 - CQRS Query 측
 *
 * SOLID:
 * - SRP: 조회 로직만 담당
 * - DIP: OrderQueryPort (인터페이스)에만 의존
 *
 * 패턴:
 * - CQRS: Command와 Query 완전 분리
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class OrderQueryService {

    private final OrderQueryPort orderQueryPort;

    public List<OrderResponse> getAllOrders() {
        return orderQueryPort.findAll().stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    @Cacheable(value = "orders", key = "#id")
    public OrderResponse getOrder(Long id) {
        log.debug("[캐시 미스] DB 조회 orderId={}", id);
        return orderQueryPort.findById(id)
                .map(OrderResponse::from)
                .orElseThrow(() -> new IllegalArgumentException("주문을 찾을 수 없습니다. id=" + id));
    }

    public List<OrderResponse> getOrdersByStatus(OrderStatus status) {
        return orderQueryPort.findByStatus(status).stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    public List<OrderResponse> getPendingOrders() {
        return orderQueryPort.findByStatus(OrderStatus.PENDING).stream()
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }

    /** [Stream 심화] 전체 주문 총 금액 합산 */
    public BigDecimal getOrdersTotalAmount() {
        return orderQueryPort.findAll().stream()
                .map(order -> order.getTotalPrice())
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    /** [Stream 심화] 상태별 주문 건수 집계 */
    public Map<OrderStatus, Long> getOrderCountByStatus() {
        return orderQueryPort.findAll().stream()
                .collect(Collectors.groupingBy(
                        order -> order.getStatus(),
                        Collectors.counting()
                ));
    }

    /** [Stream 심화] PENDING 주문 금액 내림차순 정렬 */
    public List<OrderResponse> getPendingOrdersSortedByPrice() {
        return orderQueryPort.findByStatus(OrderStatus.PENDING).stream()
                .sorted((a, b) -> b.getTotalPrice().compareTo(a.getTotalPrice()))
                .map(OrderResponse::from)
                .collect(Collectors.toList());
    }
}
"""

# ──────────────────────────────────────────────
# 14. OrderRequest DTO (OrderType 필드 추가)
# ──────────────────────────────────────────────
files["domain/order/dto/OrderRequest.java"] = """package com.order.domain.order.dto;

import com.order.domain.order.entity.OrderType;
import jakarta.validation.constraints.*;
import lombok.Getter;
import lombok.NoArgsConstructor;

import java.math.BigDecimal;

@Getter
@NoArgsConstructor
public class OrderRequest {

    @NotBlank(message = "고객명은 필수입니다.")
    @Size(max = 50, message = "고객명은 50자 이하여야 합니다.")
    private String customerName;

    @NotBlank(message = "상품명은 필수입니다.")
    @Size(max = 100, message = "상품명은 100자 이하여야 합니다.")
    private String productName;

    @NotNull(message = "수량은 필수입니다.")
    @Min(value = 1, message = "수량은 1 이상이어야 합니다.")
    private Integer quantity;

    @NotNull(message = "금액은 필수입니다.")
    @DecimalMin(value = "0.01", message = "금액은 0보다 커야 합니다.")
    private BigDecimal totalPrice;

    /** 주문 타입 - null이면 LIMIT 기본값 적용 */
    private OrderType orderType;
}
"""

# ──────────────────────────────────────────────
# 15. OrderResponse DTO (OrderType 필드 추가)
# ──────────────────────────────────────────────
files["domain/order/dto/OrderResponse.java"] = """package com.order.domain.order.dto;

import com.order.domain.order.entity.Order;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.entity.OrderType;
import lombok.Builder;
import lombok.Getter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Getter
@Builder
public class OrderResponse {

    private Long id;
    private String customerName;
    private String productName;
    private Integer quantity;
    private BigDecimal totalPrice;
    private OrderType orderType;
    private OrderStatus status;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;

    public static OrderResponse from(Order order) {
        return OrderResponse.builder()
                .id(order.getId())
                .customerName(order.getCustomerName())
                .productName(order.getProductName())
                .quantity(order.getQuantity())
                .totalPrice(order.getTotalPrice())
                .orderType(order.getOrderType())
                .status(order.getStatus())
                .createdAt(order.getCreatedAt())
                .updatedAt(order.getUpdatedAt())
                .build();
    }
}
"""

# ──────────────────────────────────────────────
# 16. OrderValidatorConfig (검증 체인 Bean 설정)
# ──────────────────────────────────────────────
files["config/OrderValidatorConfig.java"] = """package com.order.config;

import com.order.domain.order.validator.OrderValidator;
import com.order.domain.order.validator.PriceValidator;
import com.order.domain.order.validator.QuantityValidator;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * [Chain of Responsibility 조립]
 * QuantityValidator -> PriceValidator 순서로 체인 구성
 * 새 검증 규칙 추가 시: 새 Validator 구현 후 체인에 .andThen() 추가
 */
@Configuration
public class OrderValidatorConfig {

    @Bean
    public OrderValidator orderValidator(QuantityValidator qty, PriceValidator price) {
        return qty.andThen(price);
    }
}
"""

# ──────────────────────────────────────────────
# 17. OrderEventListener (Observer - Kafka 발행 분리)
# ──────────────────────────────────────────────
files["kafka/listener/OrderEventListener.java"] = """package com.order.kafka.listener;

import com.order.domain.order.event.OrderCreatedEvent;
import com.order.domain.order.event.OrderStatusChangedEvent;
import com.order.kafka.event.OrderEvent;
import com.order.kafka.producer.OrderEventProducer;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.context.event.EventListener;
import org.springframework.scheduling.annotation.Async;
import org.springframework.stereotype.Component;

import java.time.LocalDateTime;

/**
 * [Observer Pattern - Spring EventListener]
 * 도메인 이벤트를 구독하여 Kafka 발행 처리.
 * SRP: 도메인 서비스는 이벤트만 발행, Kafka 발행 책임은 이 클래스에 위임
 * DIP: 서비스가 KafkaProducer에 직접 의존하지 않음
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderEventListener {

    private final OrderEventProducer orderEventProducer;

    @Async
    @EventListener
    public void handleOrderCreated(OrderCreatedEvent event) {
        log.info("[Event] 주문 생성 이벤트 수신 orderId={}", event.getOrderId());
        OrderEvent kafkaEvent = OrderEvent.builder()
                .orderId(event.getOrderId())
                .customerName(event.getCustomerName())
                .productName(event.getProductName())
                .eventTime(LocalDateTime.now())
                .build();
        orderEventProducer.sendOrderEvent(kafkaEvent);
    }

    @Async
    @EventListener
    public void handleOrderStatusChanged(OrderStatusChangedEvent event) {
        log.info("[Event] 상태 변경 이벤트 수신 orderId={}, {} -> {}",
                event.getOrderId(), event.getPreviousStatus(), event.getNewStatus());
    }
}
"""

# ──────────────────────────────────────────────
# 18. OrderController 업데이트 (CQRS 반영)
# ──────────────────────────────────────────────
files["domain/order/controller/OrderController.java"] = """package com.order.domain.order.controller;

import com.order.common.response.ApiResponse;
import com.order.domain.order.dto.OrderRequest;
import com.order.domain.order.dto.OrderResponse;
import com.order.domain.order.entity.OrderStatus;
import com.order.domain.order.service.command.OrderCommandService;
import com.order.domain.order.service.query.OrderQueryService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

/**
 * [CQRS 반영] Command/Query 서비스 분리 주입
 * - 읽기 요청: OrderQueryService
 * - 쓰기 요청: OrderCommandService
 */
@RestController
@RequestMapping("/api/orders")
@RequiredArgsConstructor
@Tag(name = "Order API", description = "주문 관리 API")
public class OrderController {

    private final OrderCommandService orderCommandService;
    private final OrderQueryService orderQueryService;

    @GetMapping
    @Operation(summary = "전체 주문 목록 조회")
    public ApiResponse<List<OrderResponse>> getAllOrders() {
        return ApiResponse.success(orderQueryService.getAllOrders());
    }

    @GetMapping("/{id}")
    @Operation(summary = "단건 주문 조회 (Redis 캐시 적용)")
    public ApiResponse<OrderResponse> getOrder(@PathVariable Long id) {
        return ApiResponse.success(orderQueryService.getOrder(id));
    }

    @GetMapping("/status/{status}")
    @Operation(summary = "상태별 주문 조회")
    public ApiResponse<List<OrderResponse>> getOrdersByStatus(@PathVariable OrderStatus status) {
        return ApiResponse.success(orderQueryService.getOrdersByStatus(status));
    }

    @GetMapping("/pending/sorted")
    @Operation(summary = "PENDING 주문 금액 내림차순 조회")
    public ApiResponse<List<OrderResponse>> getPendingOrdersSortedByPrice() {
        return ApiResponse.success(orderQueryService.getPendingOrdersSortedByPrice());
    }

    @GetMapping("/stats/total-amount")
    @Operation(summary = "전체 주문 총 금액 합산")
    public ApiResponse<BigDecimal> getTotalAmount() {
        return ApiResponse.success(orderQueryService.getOrdersTotalAmount());
    }

    @GetMapping("/stats/count-by-status")
    @Operation(summary = "상태별 주문 건수 집계")
    public ApiResponse<Map<OrderStatus, Long>> getCountByStatus() {
        return ApiResponse.success(orderQueryService.getOrderCountByStatus());
    }

    @PostMapping
    @ResponseStatus(HttpStatus.CREATED)
    @Operation(summary = "주문 생성 (Kafka 이벤트 발행)")
    public ApiResponse<OrderResponse> createOrder(@RequestBody @Valid OrderRequest request) {
        return ApiResponse.success("주문이 생성되었습니다.", orderCommandService.createOrder(request));
    }

    @PatchMapping("/{id}/status")
    @Operation(summary = "주문 상태 변경 (State Machine 검증)")
    public ApiResponse<OrderResponse> updateStatus(
            @PathVariable Long id,
            @RequestParam OrderStatus status) {
        return ApiResponse.success("주문 상태가 변경되었습니다.", orderCommandService.updateOrderStatus(id, status));
    }
}
"""

# ──────────────────────────────────────────────
# 파일 쓰기 실행
# ──────────────────────────────────────────────
success = 0
for rel_path, content in files.items():
    full_path = os.path.join(BASE, rel_path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"OK  {rel_path}")
    success += 1

print(f"\n총 {success}개 파일 생성 완료")
