package com.exchange.marketdata.infrastructure.redis;

import com.exchange.marketdata.domain.ticker.dto.TickerDto;
import com.exchange.marketdata.domain.ticker.service.TickerService;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.redis.connection.Message;
import org.springframework.data.redis.connection.MessageListener;
import org.springframework.stereotype.Component;

/**
 * Redis Pub/Sub 구독자
 * 다른 인스턴스가 발행한 "market.ticker.*" 메시지를 수신
 * → WebSocket /topic/ticker/{symbol} 브로드캐스트
 *
 * 단일 인스턴스에서는 불필요하지만, 수평 확장 시 모든 인스턴스에 시세 동기화 보장
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class MarketDataRedisSubscriber implements MessageListener {

    private final TickerService tickerService;
    private final ObjectMapper objectMapper;

    @Override
    public void onMessage(Message message, byte[] pattern) {
        try {
            String body    = new String(message.getBody());
            String channel = new String(message.getChannel());
            // channel = "market.ticker.{symbol}"
            String symbol  = channel.substring(channel.lastIndexOf('.') + 1);

            TickerDto ticker = objectMapper.readValue(body, TickerDto.class);
            tickerService.broadcastToWebSocket(symbol, ticker);
            log.debug("[Redis Sub] 시세 수신 — symbol={}, price={}", symbol, ticker.getPrice());
        } catch (Exception e) {
            log.error("[Redis Sub] 메시지 처리 실패: {}", e.getMessage());
        }
    }
}
