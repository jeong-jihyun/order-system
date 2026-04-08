package com.exchange.account.domain.holding.repository;

import com.exchange.account.domain.holding.entity.Holding;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Lock;
import org.springframework.data.jpa.repository.Query;

import jakarta.persistence.LockModeType;
import java.util.List;
import java.util.Optional;

public interface HoldingRepository extends JpaRepository<Holding, Long> {

    List<Holding> findByUserId(Long userId);

    @Lock(LockModeType.PESSIMISTIC_WRITE)
    @Query("SELECT h FROM Holding h WHERE h.user.id = :userId AND h.symbol = :symbol")
    Optional<Holding> findByUserIdAndSymbolForUpdate(Long userId, String symbol);

    Optional<Holding> findByUserIdAndSymbol(Long userId, String symbol);
}
