package com.exchange.marketdata.domain.ticker.controller;

import com.exchange.marketdata.domain.ticker.dto.TickerDto;
import com.exchange.marketdata.domain.ticker.service.TickerService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.messaging.handler.annotation.DestinationVariable;
import org.springframework.messaging.handler.annotation.MessageMapping;
import org.springframework.messaging.handler.annotation.SendTo;
import org.springframework.stereotype.Controller;

import java.util.Optional;

/**
 * STOMP 메시지 핸들러
 * 클라이언트가 /app/subscribe/{symbol} 으로 구독 요청 시
 * 현재 시세를 즉시 /topic/ticker/{symbol} 로 전송
 */
@Slf4j
@Controller
@RequiredArgsConstructor
public class MarketWebSocketController {

    private final TickerService tickerService;

    @MessageMapping("/subscribe/{symbol}")
    @SendTo("/topic/ticker/{symbol}")
    public TickerDto subscribe(@DestinationVariable String symbol) {
        log.debug("[WS] 구독 요청 — symbol={}", symbol);
        return tickerService.getTicker(symbol)
                .orElse(TickerDto.builder().symbol(symbol).build());
    }
}
