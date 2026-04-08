package com.exchange.order.domain.order.entity;

import java.util.Set;
import java.util.EnumSet;

/**
 * 주문 상태 State Machine
 * canTransitionTo()로 잘못된 상태 전이를 사전 차단
 */
public enum OrderStatus {
    PENDING {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.of(PROCESSING, CANCELLED);
        }
    },
    PROCESSING {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.of(COMPLETED, CANCELLED);
        }
    },
    COMPLETED {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.noneOf(OrderStatus.class);
        }
    },
    CANCELLED {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.noneOf(OrderStatus.class);
        }
    };

    public abstract Set<OrderStatus> allowedTransitions();

    public boolean canTransitionTo(OrderStatus next) {
        return allowedTransitions().contains(next);
    }

    public boolean isTerminal() {
        return this == COMPLETED || this == CANCELLED;
    }
}
