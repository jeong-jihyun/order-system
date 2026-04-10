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
            return EnumSet.of(PARTIALLY_FILLED, COMPLETED, CANCELLED, EXPIRED);
        }
    },
    /** 부분 체결 — 잔여 수량이 호가창에 남아있음 (FIX 5.0 OrdStatus=1) */
    PARTIALLY_FILLED {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.of(PARTIALLY_FILLED, COMPLETED, CANCELLED, EXPIRED);
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
    },
    /** IOC/FOK/GTD 주문 만료 (FIX 5.0 OrdStatus=C) */
    EXPIRED {
        @Override public Set<OrderStatus> allowedTransitions() {
            return EnumSet.noneOf(OrderStatus.class);
        }
    };

    public abstract Set<OrderStatus> allowedTransitions();

    public boolean canTransitionTo(OrderStatus next) {
        return allowedTransitions().contains(next);
    }

    public boolean isTerminal() {
        return this == COMPLETED || this == CANCELLED || this == EXPIRED;
    }
}
