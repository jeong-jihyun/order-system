package com.exchange.order.domain.outbox.service;

import com.exchange.order.domain.outbox.entity.OutboxEvent;
import com.exchange.order.domain.outbox.repository.OutboxEventRepository;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

/**
 * OutboxEvent 저장을 담당하는 서비스
 * — 반드시 OrderCommandService와 동일 트랜잭션에서 호출
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class OutboxService {

    private final OutboxEventRepository outboxEventRepository;
    private final ObjectMapper objectMapper;

    public void save(String aggregateType, Long aggregateId,
                     String eventType, String topic, Object payload) {
        try {
            String json = objectMapper.writeValueAsString(payload);
            OutboxEvent outboxEvent = OutboxEvent.builder()
                    .aggregateType(aggregateType)
                    .aggregateId(aggregateId)
                    .eventType(eventType)
                    .topic(topic)
                    .payload(json)
                    .build();
            outboxEventRepository.save(outboxEvent);
            log.debug("[Outbox] 이벤트 저장 — type={}, aggregateId={}", eventType, aggregateId);
        } catch (JsonProcessingException e) {
            throw new RuntimeException("Outbox 이벤트 직렬화 실패: " + eventType, e);
        }
    }
}
