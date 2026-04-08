package com.order.domain.order.strategy;

import com.order.domain.order.entity.OrderType;
import org.springframework.stereotype.Component;

import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

/**
 * [Factory Pattern]
 * Spring이 주입한 모든 OrderStrategy 구현체를 Map으로 관리.
 * OCP: 새 Strategy 추가 시 Factory 코드 수정 불필요 - 자동 등록됨
 * DIP: 고수준이 저수준(구체 전략)에 직접 의존하지 않음
 */
@Component
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
