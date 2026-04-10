package com.exchange.settlement.domain.settlement.repository;

import com.exchange.settlement.domain.settlement.entity.SettlementRecord;
import com.exchange.settlement.domain.settlement.entity.SettlementStatus;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;

public interface SettlementRecordRepository extends JpaRepository<SettlementRecord, Long> {

    /**
     * T+2 정산 처리 대상 조회 (오늘 정산일인 SCHEDULED 레코드)
     */
    @Query("SELECT s FROM SettlementRecord s " +
           "WHERE s.settlementDate <= :today AND s.status = :status")
    List<SettlementRecord> findDueSettlements(@Param("today") LocalDate today,
                                              @Param("status") SettlementStatus status);

    List<SettlementRecord> findByUsernameOrderByExecutedAtDesc(String username);

    /**
     * @deprecated executedAt 없이 orderId+side 만으로는 부분 체결 중복 검사 불가
     *             existsByOrderIdAndSideAndExecutedAt 사용 권고
     */
    @Deprecated
    boolean existsByOrderIdAndSide(Long orderId, String side);

    /** 부분 체결 정산 중복 방지 — (orderId, side, executedAt) 3중 복합 조건 */
    boolean existsByOrderIdAndSideAndExecutedAt(Long orderId, String side, LocalDateTime executedAt);
}
