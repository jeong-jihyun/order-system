package com.order.domain.order.port;

import com.order.domain.order.entity.Order;

/**
 * [DIP + ISP] 쓰기 전용 포트 인터페이스
 * - ISP: 읽기/쓰기를 분리함으로써 불필요한 의존 방지
 * - CQRS 패턴으로의 자연스러운 전환 지원
 */
public interface OrderCommandPort {
    Order save(Order order);
    void deleteById(Long id);
}
