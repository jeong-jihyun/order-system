package com.exchange.order.domain.order.port;

import com.exchange.order.domain.order.entity.Order;

public interface OrderCommandPort {
    Order save(Order order);
    void deleteById(Long id);
}
