package com.exchange.gateway.filter;

import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import com.exchange.gateway.security.JwtUtil;
import lombok.extern.slf4j.Slf4j;
import org.springframework.cloud.gateway.filter.GatewayFilter;
import org.springframework.cloud.gateway.filter.factory.AbstractGatewayFilterFactory;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ServerWebExchange;
import reactor.core.publisher.Mono;

/**
 * JWT 인증 GatewayFilterFactory
 *
 * 동작:
 * 1. Authorization: Bearer {token} 헤더 추출
 * 2. JWT 서명/만료 검증
 * 3. 성공 → X-User-Name, X-User-Role 헤더를 하위 서비스에 전달
 * 4. 실패 → 401 Unauthorized 즉시 반환
 *
 * 설정: application.yml 라우트의 filters 에 "JwtAuthentication" 으로 적용
 */
@Slf4j
@Component
public class JwtAuthenticationFilter
        extends AbstractGatewayFilterFactory<JwtAuthenticationFilter.Config> {

    private final JwtUtil jwtUtil;

    public JwtAuthenticationFilter(JwtUtil jwtUtil) {
        super(Config.class);
        this.jwtUtil = jwtUtil;
    }

    @Override
    public GatewayFilter apply(Config config) {
        return (exchange, chain) -> {
            String authHeader = exchange.getRequest()
                    .getHeaders().getFirst(HttpHeaders.AUTHORIZATION);

            if (authHeader == null || !authHeader.startsWith("Bearer ")) {
                return unauthorized(exchange, "Authorization 헤더가 없습니다.");
            }

            String token = authHeader.substring(7);
            try {
                DecodedJWT jwt = jwtUtil.verify(token);
                String username = jwt.getSubject();
                String role     = jwt.getClaim("role").asString();

                // 하위 서비스에 사용자 정보 전달 (헤더 위조 방지: 클라이언트 헤더 제거 후 재설정)
                ServerWebExchange mutated = exchange.mutate()
                        .request(r -> r.headers(headers -> {
                            headers.remove("X-User-Name");
                            headers.remove("X-User-Role");
                            headers.add("X-User-Name", username);
                            headers.add("X-User-Role", role != null ? role : "USER");
                        }))
                        .build();

                log.debug("[Gateway] JWT 인증 성공 — user={}, role={}", username, role);
                return chain.filter(mutated);

            } catch (JWTVerificationException e) {
                log.warn("[Gateway] JWT 인증 실패 — {}", e.getMessage());
                return unauthorized(exchange, "유효하지 않은 토큰입니다.");
            }
        };
    }

    private Mono<Void> unauthorized(ServerWebExchange exchange, String message) {
        exchange.getResponse().setStatusCode(HttpStatus.UNAUTHORIZED);
        exchange.getResponse().getHeaders().add("Content-Type", "application/json");
        String body = "{\"success\":false,\"message\":\"" + message + "\"}";
        var buffer = exchange.getResponse().bufferFactory().wrap(body.getBytes());
        return exchange.getResponse().writeWith(Mono.just(buffer));
    }

    public static class Config {}
}
