package com.exchange.order.domain.outbox.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.time.LocalDateTime;

/**
 * Outbox Pattern — 이벤트를 DB에 먼저 저장
 *
 * [왜 Outbox Pattern인가?]
 * 기존: DB 저장 성공 → Kafka 발행 (비동기) → Kafka 실패 시 이벤트 소실
 * 개선: DB 저장 + OutboxEvent 저장 (단일 트랜잭션) → 스케줄러가 안전하게 Kafka 발행
 *
 * 보장: DB 커밋 = 이벤트 저장 보장 → 최소 1회 발행(at-least-once) 달성
 */
@Entity
@Table(name = "outbox_events",
       indexes = {
           @Index(name = "idx_outbox_status_created", columnList = "status, createdAt"),
           @Index(name = "idx_outbox_aggregate", columnList = "aggregateType, aggregateId")
       })
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
@Builder
@AllArgsConstructor
public class OutboxEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** 집합체 타입 (예: "Order") */
    @Column(nullable = false, length = 50)
    private String aggregateType;

    /** 집합체 ID (주문 ID) */
    @Column(nullable = false)
    private Long aggregateId;

    /** 이벤트 타입 (예: "ORDER_CREATED", "ORDER_STATUS_CHANGED") */
    @Column(nullable = false, length = 100)
    private String eventType;

    /** JSON 직렬화된 이벤트 페이로드 */
    @Column(nullable = false, columnDefinition = "TEXT")
    private String payload;

    /** Kafka 토픽 */
    @Column(nullable = false, length = 100)
    private String topic;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false, length = 20)
    @Builder.Default
    private OutboxStatus status = OutboxStatus.PENDING;

    /** 재시도 횟수 */
    @Column(nullable = false)
    @Builder.Default
    private int retryCount = 0;

    /** 마지막 오류 메시지 */
    @Column(length = 500)
    private String lastError;

    @CreationTimestamp
    @Column(updatable = false)
    private LocalDateTime createdAt;

    private LocalDateTime publishedAt;

    public void markPublished() {
        this.status = OutboxStatus.PUBLISHED;
        this.publishedAt = LocalDateTime.now();
    }

    public void markFailed(String errorMessage) {
        this.retryCount++;
        this.lastError = errorMessage;
        if (this.retryCount >= 5) {
            this.status = OutboxStatus.DEAD_LETTER;
        }
        // PENDING 유지 — 다음 스케줄러 실행 시 재시도
    }
}
