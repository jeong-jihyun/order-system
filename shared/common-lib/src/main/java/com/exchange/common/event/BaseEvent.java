package com.exchange.common.event;

import lombok.Getter;
import java.time.LocalDateTime;
import java.util.UUID;

/**
 * 모든 도메인 이벤트의 기반 클래스
 * - eventId: 멱등성 보장을 위한 고유 ID
 * - occurredAt: 이벤트 발생 시각
 */
@Getter
public abstract class BaseEvent {
    private final String eventId = UUID.randomUUID().toString();
    private final LocalDateTime occurredAt = LocalDateTime.now();
    public abstract String getEventType();
}
