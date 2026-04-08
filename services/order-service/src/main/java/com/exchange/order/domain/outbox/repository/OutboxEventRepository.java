package com.exchange.order.domain.outbox.repository;

import com.exchange.order.domain.outbox.entity.OutboxEvent;
import com.exchange.order.domain.outbox.entity.OutboxStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.util.List;

public interface OutboxEventRepository extends JpaRepository<OutboxEvent, Long> {

    /**
     * PENDING 상태 중 재시도 횟수 5회 미만인 이벤트만 조회
     * 생성 시각 순 정렬 — FIFO 처리
     */
    @Query("SELECT o FROM OutboxEvent o WHERE o.status = :status AND o.retryCount < :maxRetry ORDER BY o.createdAt ASC")
    List<OutboxEvent> findPendingEvents(
            @Param("status") OutboxStatus status,
            @Param("maxRetry") int maxRetry);
}
