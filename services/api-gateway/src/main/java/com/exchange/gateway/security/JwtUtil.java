package com.exchange.gateway.security;

import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/**
 * JWT 검증 유틸 (Gateway — 발급하지 않고 검증만 수행)
 */
@Component
public class JwtUtil {

    @Value("${jwt.secret}")
    private String secret;

    public DecodedJWT verify(String token) throws JWTVerificationException {
        return JWT.require(Algorithm.HMAC256(secret))
                .withIssuer("exchange")
                .build()
                .verify(token);
    }

    public String extractUsername(String token) {
        return verify(token).getSubject();
    }

    public String extractRole(String token) {
        return verify(token).getClaim("role").asString();
    }
}
