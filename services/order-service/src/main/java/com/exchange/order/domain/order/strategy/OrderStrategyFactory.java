package com.exchange.order.domain.order.strategy;

import com.exchange.order.domain.order.entity.OrderType;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * Factory Pattern — Spring DI로 모든 OrderStrategy 구현체 자동 수집
 * OCP: 새 주문 타입 추가 시 Strategy 클래스만 추가하면 자동 등록
 */
@Slf4j
@Component
public class OrderStrategyFactory {

    private final Map<OrderType, OrderStrategy> strategies;

    public OrderStrategyFactory(List<OrderStrategy> strategyList) {
        this.strategies = strategyList.stream()
                .collect(Collectors.toMap(OrderStrategy::getSupportedType, s -> s));
        log.info("[StrategyFactory] 등록된 전략: {}", strategies.keySet());
    }

    public OrderStrategy getStrategy(OrderType type) {
        OrderStrategy strategy = strategies.get(type);
        if (strategy == null) {
            throw new IllegalArgumentException("지원하지 않는 주문 타입: " + type);
        }
        return strategy;
    }
}
