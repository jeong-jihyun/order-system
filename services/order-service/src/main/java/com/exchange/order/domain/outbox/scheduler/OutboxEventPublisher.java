package com.exchange.order.domain.outbox.scheduler;

import com.exchange.order.domain.outbox.entity.OutboxEvent;
import com.exchange.order.domain.outbox.entity.OutboxStatus;
import com.exchange.order.domain.outbox.repository.OutboxEventRepository;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

/**
 * Outbox Pattern — Relay 스케줄러
 *
 * 동작 흐름:
 * 1. PENDING 상태의 OutboxEvent 조회
 * 2. Kafka에 발행 시도
 * 3. 성공 → PUBLISHED 마킹
 * 4. 실패 → retryCount++ (5회 초과 시 DEAD_LETTER)
 *
 * @Transactional: Kafka 발행 결과가 DB에 원자적으로 반영
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class OutboxEventPublisher {

    private final OutboxEventRepository outboxEventRepository;
    private final KafkaTemplate<String, String> kafkaTemplate;
    private final ObjectMapper objectMapper;

    @Value("${outbox.scheduler.max-retry:5}")
    private int maxRetry;

    @Scheduled(fixedDelayString = "${outbox.scheduler.fixed-delay-ms:5000}")
    @Transactional
    public void publishPendingEvents() {
        List<OutboxEvent> pendingEvents =
                outboxEventRepository.findPendingEvents(OutboxStatus.PENDING, maxRetry);

        if (pendingEvents.isEmpty()) return;

        log.debug("[Outbox] 발행 대상 이벤트 {}건 처리 시작", pendingEvents.size());

        for (OutboxEvent event : pendingEvents) {
            try {
                kafkaTemplate.send(event.getTopic(),
                                   String.valueOf(event.getAggregateId()),
                                   event.getPayload())
                        .get(); // 동기 대기 — 발행 확인 보장

                event.markPublished();
                log.info("[Outbox] 발행 완료 — id={}, type={}, aggregateId={}",
                        event.getId(), event.getEventType(), event.getAggregateId());
            } catch (Exception e) {
                event.markFailed(e.getMessage());
                log.error("[Outbox] 발행 실패 — id={}, retry={}, error={}",
                        event.getId(), event.getRetryCount(), e.getMessage());
            }
        }
    }
}
