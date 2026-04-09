# Day 7 보충 — 백엔드 WebSocket 통신 상세 가이드

> 서비스: `market-data-service` | 날짜: 2026-04-09

---

## 1. 전체 흐름 한눈에 보기

```
[trading-engine]
  매칭 완료 → Kafka: order-status-events 발행
        ↓
[market-data-service]
  OrderEventKafkaConsumer.consume()
        ↓
  TickerService.updatePrice()
        ├─ Redis에 현재 시세 저장 (ticker:AAPL)
        ├─ Redis Pub/Sub 발행 (market.ticker.AAPL) ← 멀티 인스턴스 동기화용
        └─ SimpMessagingTemplate → /topic/ticker/AAPL 브로드캐스트
                                              ↓
                                   [브라우저 클라이언트들]
                                   구독 중인 모든 클라이언트 수신
```

---

## 2. WebSocket vs HTTP 차이

| | HTTP | WebSocket |
|--|------|-----------|
| 연결 방식 | 요청마다 연결/해제 | 한번 연결 후 유지 |
| 통신 방향 | 클라이언트 → 서버 (단방향) | 양방향 실시간 |
| 서버 → 클라이언트 | 불가 (클라이언트가 먼저 요청해야 함) | 가능 (서버가 먼저 보낼 수 있음) |
| 사용처 | API 호출, 페이지 요청 | 실시간 시세, 채팅, 알림 |
| 오버헤드 | 요청마다 헤더 재전송 | 연결 1회 후 경량 프레임만 전송 |

---

## 3. STOMP 프로토콜

> WebSocket은 날 것의 소켓. STOMP는 그 위에 메시지 규약을 추가한 프로토콜.

**STOMP 메시지 구조:**
```
COMMAND
header1: value1
header2: value2

body
^@
```

**실제 STOMP 명령어:**

| 명령어 | 방향 | 설명 |
|--------|------|------|
| `CONNECT` | 클라 → 서버 | 연결 요청 |
| `CONNECTED` | 서버 → 클라 | 연결 수락 |
| `SUBSCRIBE` | 클라 → 서버 | 특정 경로 구독 |
| `SEND` | 클라 → 서버 | 메시지 전송 |
| `MESSAGE` | 서버 → 클라 | 메시지 전달 |
| `DISCONNECT` | 클라 → 서버 | 연결 해제 |

---

## 4. WebSocketConfig.java — 설정 분석

```java
@Configuration
@EnableWebSocketMessageBroker   // STOMP 기반 WebSocket 활성화
public class WebSocketConfig implements WebSocketMessageBrokerConfigurer {

    @Override
    public void configureMessageBroker(MessageBrokerRegistry registry) {
        // ① 인메모리 브로커 — /topic 경로로 브로드캐스트
        registry.enableSimpleBroker("/topic");

        // ② 클라이언트 → 서버 메시지의 prefix
        registry.setApplicationDestinationPrefixes("/app");
    }

    @Override
    public void registerStompEndpoints(StompEndpointRegistry registry) {
        // ③ WebSocket 연결 엔드포인트: ws://localhost:8083/ws
        registry.addEndpoint("/ws")
                .setAllowedOriginPatterns("*")   // CORS 허용
                .withSockJS();                    // WebSocket 미지원 브라우저를 위한 폴백
    }
}
```

**경로 구조 이해:**

```
/app/subscribe/AAPL   ← 클라이언트에서 서버로 보내는 메시지
│    │
│    └── ApplicationDestinationPrefix = /app
│         → @MessageMapping("/subscribe/AAPL") 메서드가 처리

/topic/ticker/AAPL    ← 서버에서 클라이언트로 브로드캐스트
│
└── SimpleBroker = /topic
     → 이 경로를 구독하는 모든 클라이언트에게 전달
```

**SockJS란?**
```
WebSocket 지원 브라우저   → 직접 ws:// 연결
WebSocket 미지원 브라우저 → SockJS가 HTTP Long-Polling 등으로 대체
→ 구버전 브라우저에서도 동작 보장
```

---

## 5. MarketWebSocketController.java — 메시지 핸들러

```java
@Controller
@RequiredArgsConstructor
public class MarketWebSocketController {

    private final TickerService tickerService;

    @MessageMapping("/subscribe/{symbol}")   // /app/subscribe/AAPL 수신
    @SendTo("/topic/ticker/{symbol}")         // /topic/ticker/AAPL 으로 응답
    public TickerDto subscribe(@DestinationVariable String symbol) {
        // 구독 즉시 현재 시세 1회 전송 (초기값)
        return tickerService.getTicker(symbol)
                .orElse(TickerDto.builder().symbol(symbol).build());
    }
}
```

**어노테이션 역할:**

| 어노테이션 | 역할 |
|-----------|------|
| `@MessageMapping("/subscribe/{symbol}")` | HTTP의 `@PostMapping`과 같음. STOMP 메시지 수신 경로 |
| `@SendTo("/topic/ticker/{symbol}")` | 반환값을 이 경로를 구독하는 모든 클라이언트에게 전송 |
| `@DestinationVariable String symbol` | 경로 변수 추출 (`{symbol}` → "AAPL") |

---

## 6. TickerService — 핵심 3가지 동작

### 6-1. Redis에 시세 저장

```java
private void saveToRedis(String key, TickerDto ticker) {
    String json = objectMapper.writeValueAsString(ticker);
    stringRedisTemplate.opsForValue().set(
        key,                         // "ticker:AAPL"
        json,                        // JSON 직렬화
        Duration.ofSeconds(ttlSeconds) // TTL 5분
    );
}
```

**왜 Redis에 저장하나?**
- 클라이언트가 나중에 접속할 때 현재 시세를 즉시 제공 (`getTicker()`)
- WebSocket은 "실시간 스트림" → 과거 시세는 Redis에서 조회

### 6-2. Redis Pub/Sub 발행 (멀티 인스턴스 동기화)

```java
private void publishToRedis(String symbol, TickerDto ticker) {
    String channel = "market.ticker." + symbol; // "market.ticker.AAPL"
    stringRedisTemplate.convertAndSend(channel, objectMapper.writeValueAsString(ticker));
}
```

**왜 필요한가?**

```
인스턴스A ─ 클라이언트 1, 2, 3 연결
인스턴스B ─ 클라이언트 4, 5, 6 연결

Kafka 메시지가 인스턴스A에만 도착
    ↓ Redis Pub/Sub 없으면
인스턴스A의 클라이언트 1,2,3만 시세 수신 💥
인스턴스B의 클라이언트 4,5,6은 시세 못 받음

    ↓ Redis Pub/Sub 있으면
인스턴스A → Redis Pub/Sub 발행
인스턴스B → Redis Sub 수신 → WebSocket 브로드캐스트 ✅
모든 클라이언트 동일한 시세 수신
```

### 6-3. WebSocket 브로드캐스트

```java
private void broadcastToWebSocket(String symbol, TickerDto ticker) {
    messagingTemplate.convertAndSend(topicPrefix + symbol, ticker);
    // → /topic/ticker/AAPL 구독 중인 모든 클라이언트에게 전송
}
```

**`SimpMessagingTemplate`:**
- Spring이 제공하는 WebSocket 메시지 발행 도구
- 컨트롤러 밖(Service, Scheduler 등)에서 WebSocket 메시지를 보낼 때 사용
- `convertAndSend(destination, payload)` → JSON 자동 직렬화 후 전송

---

## 7. MarketDataRedisSubscriber — Redis Pub/Sub 수신

```java
@Component
public class MarketDataRedisSubscriber implements MessageListener {

    @Override
    public void onMessage(Message message, byte[] pattern) {
        String body    = new String(message.getBody());    // JSON 페이로드
        String channel = new String(message.getChannel()); // "market.ticker.AAPL"
        String symbol  = channel.substring(channel.lastIndexOf('.') + 1); // "AAPL"

        TickerDto ticker = objectMapper.readValue(body, TickerDto.class);
        tickerService.broadcastToWebSocket(symbol, ticker); // WebSocket으로 전달
    }
}
```

**RedisConfig에서 패턴 구독 등록:**

```java
// "market.ticker.*" 패턴의 모든 채널 구독
container.addMessageListener(listenerAdapter, new PatternTopic("market.ticker.*"));
// market.ticker.AAPL
// market.ticker.TSLA
// market.ticker.BTC-USD → 전부 수신
```

---

## 8. TickerDto — WebSocket으로 전달되는 데이터

```java
public class TickerDto {
    private String symbol;         // "AAPL"
    private BigDecimal price;      // 현재가: 185.50
    private BigDecimal open;       // 시가: 183.00
    private BigDecimal high;       // 고가: 186.20
    private BigDecimal low;        // 저가: 182.50
    private BigDecimal prevClose;  // 전일 종가: 182.00
    private BigDecimal change;     // 변동금액: +3.50
    private BigDecimal changeRate; // 변동률: +1.92%
    private Long volume;           // 거래량: 1500
    private BigDecimal turnover;   // 거래대금: 278,250
    private LocalDateTime timestamp;
}
```

**클라이언트가 받는 JSON:**
```json
{
  "symbol": "AAPL",
  "price": 185.50,
  "open": 183.00,
  "high": 186.20,
  "low": 182.50,
  "prevClose": 182.00,
  "change": 3.50,
  "changeRate": 1.92,
  "volume": 1500,
  "turnover": 278250.00,
  "timestamp": "2026-04-09T14:30:00"
}
```

---

## 9. 프론트엔드 연결 방법 (참고)

```typescript
// SockJS + STOMP 클라이언트 연결 (참고용)
import SockJS from 'sockjs-client';
import { Client } from '@stomp/stompjs';

const client = new Client({
    webSocketFactory: () => new SockJS('http://localhost:8083/ws'),
    onConnect: () => {
        // ① 시세 구독
        client.subscribe('/topic/ticker/AAPL', (message) => {
            const ticker = JSON.parse(message.body);
            console.log('현재가:', ticker.price);
        });

        // ② 서버에 구독 요청 (최초 시세 수신)
        client.publish({ destination: '/app/subscribe/AAPL' });
    }
});

client.activate();
```

---

## 10. 전체 구조 클래스 다이어그램

```
[Kafka: order-status-events]
        ↓
OrderEventKafkaConsumer
        │ consume(message)
        ↓
TickerService
  ├─ saveToRedis()
  │    └─ StringRedisTemplate.set("ticker:AAPL", json, TTL 5분)
  │
  ├─ publishToRedis()
  │    └─ StringRedisTemplate.convertAndSend("market.ticker.AAPL", json)
  │                                   ↓
  │                       [Redis Pub/Sub]
  │                                   ↓
  │                       MarketDataRedisSubscriber.onMessage()
  │                                   ↓ (다른 인스턴스의 브로드캐스트)
  │                       TickerService.broadcastToWebSocket()
  │
  └─ broadcastToWebSocket()
       └─ SimpMessagingTemplate.convertAndSend("/topic/ticker/AAPL", ticker)
                                       ↓
                           [STOMP SimpleBroker]
                                       ↓
                           구독 중인 모든 브라우저 클라이언트
```

---

## 11. 실무 포인트 요약

| 개념 | 설명 |
|------|------|
| `@EnableWebSocketMessageBroker` | STOMP 기반 WebSocket 활성화 |
| `enableSimpleBroker("/topic")` | 인메모리 브로커. 운영에서는 외부 브로커(RabbitMQ) 권장 |
| `setApplicationDestinationPrefixes("/app")` | 클라 → 서버 메시지 prefix. `/app` 붙은 것만 `@MessageMapping`이 처리 |
| `SimpMessagingTemplate` | 서비스 레이어에서 WebSocket 발행할 때 사용 |
| `@SendTo` | 컨트롤러 반환값을 지정 경로로 자동 전송 |
| `SockJS` | 구버전 브라우저용 WebSocket 폴백 |
| Redis Pub/Sub | 멀티 인스턴스 환경에서 모든 서버가 동일한 메시지를 클라이언트에게 전송 |
| `PatternTopic("market.ticker.*")` | 와일드카드로 여러 채널 한번에 구독 |
