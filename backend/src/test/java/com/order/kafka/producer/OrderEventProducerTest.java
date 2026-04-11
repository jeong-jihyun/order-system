package com.order.kafka.producer;

import com.order.kafka.event.OrderEvent;
import org.junit.jupiter.api.Test;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.MockitoAnnotations;
import org.springframework.kafka.core.KafkaTemplate;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.concurrent.CompletableFuture;

class OrderEventProducerTest {

    @Mock
    private KafkaTemplate<String, OrderEvent> kafkaTemplate;

    @InjectMocks
    private OrderEventProducer orderEventProducer;

    public OrderEventProducerTest() {
        MockitoAnnotations.openMocks(this);
    }

    @Test
    void sendOrderEvent_shouldSendMessage() {
        // given
        OrderEvent event = new OrderEvent();
        event.setOrderId(123L);
        CompletableFuture future = new CompletableFuture();
        future.complete(null);
        when(kafkaTemplate.send(any(), any(), any())).thenReturn(future);

        // when
        orderEventProducer.sendOrderEvent(event);

        // then
        verify(kafkaTemplate).send(any(), eq("123"), eq(event));
    }
}
