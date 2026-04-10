package com.exchange.order.kafka.consumer;

import com.exchange.order.domain.order.entity.Order;
import com.exchange.order.domain.order.entity.OrderStatus;
import com.exchange.order.domain.order.repository.OrderRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * trading-engine의 체결 이벤트(order-status-events)를 수신하여
 * 주문 상태를 PENDING → PROCESSING → COMPLETED 로 업데이트
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OrderStatusEventConsumer {

    private final OrderRepository orderRepository;
    private final ObjectMapper objectMapper;

    @Transactional
    @KafkaListener(topics = "order-status-events", groupId = "order-service-status-group")
    public void consume(String message) {
        try {
            JsonNode node = objectMapper.readTree(message);
            Long buyOrderId  = node.get("buyOrderId").asLong();
            Long sellOrderId = node.get("sellOrderId").asLong();
            boolean buyFilled  = node.get("buyFilled").asBoolean();
            boolean sellFilled = node.get("sellFilled").asBoolean();

            log.info("[OrderStatusConsumer] 체결 이벤트 수신: buyId={}, sellId={}, buyFilled={}, sellFilled={}",
                    buyOrderId, sellOrderId, buyFilled, sellFilled);

            updateOrderStatus(buyOrderId, buyFilled);
            updateOrderStatus(sellOrderId, sellFilled);

        } catch (Exception e) {
            log.error("[OrderStatusConsumer] 처리 실패: {}", e.getMessage(), e);
        }
    }

    private void updateOrderStatus(Long orderId, boolean filled) {
        orderRepository.findById(orderId).ifPresentOrElse(order -> {
            try {
                // PENDING → PROCESSING
                if (order.getStatus() == OrderStatus.PENDING) {
                    order.updateStatus(OrderStatus.PROCESSING);
                }
                // PROCESSING → COMPLETED or PARTIALLY_FILLED
                if (order.getStatus() == OrderStatus.PROCESSING) {
                    order.updateStatus(filled ? OrderStatus.COMPLETED : OrderStatus.PARTIALLY_FILLED);
                }
                // PARTIALLY_FILLED → COMPLETED
                else if (order.getStatus() == OrderStatus.PARTIALLY_FILLED && filled) {
                    order.updateStatus(OrderStatus.COMPLETED);
                }
                orderRepository.save(order);
                log.info("[OrderStatusConsumer] 주문 {} 상태 → {}", orderId, order.getStatus());
            } catch (Exception e) {
                log.warn("[OrderStatusConsumer] 주문 {} 상태 전환 실패: {}", orderId, e.getMessage());
            }
        }, () -> log.warn("[OrderStatusConsumer] 주문 {} 없음", orderId));
    }
}
