package com.exchange.account.security;

import com.auth0.jwt.JWT;
import com.auth0.jwt.algorithms.Algorithm;
import com.auth0.jwt.exceptions.JWTVerificationException;
import com.auth0.jwt.interfaces.DecodedJWT;
import com.exchange.account.domain.user.entity.User;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.util.Date;

/**
 * JWT 발급 + 검증
 * HMAC256 서명, 24시간 만료, issuer = "exchange"
 */
@Component
public class JwtProvider {

    @Value("${jwt.secret}")
    private String secret;

    @Value("${jwt.expiration-hours:24}")
    private long expirationHours;

    public String generateToken(User user) {
        long now = System.currentTimeMillis();
        return JWT.create()
                .withIssuer("exchange")
                .withSubject(user.getUsername())
                .withClaim("role", user.getRole().name())
                .withClaim("userId", user.getId())
                .withIssuedAt(new Date(now))
                .withExpiresAt(new Date(now + expirationHours * 3600_000L))
                .sign(Algorithm.HMAC256(secret));
    }

    public DecodedJWT verify(String token) throws JWTVerificationException {
        return JWT.require(Algorithm.HMAC256(secret))
                .withIssuer("exchange")
                .build()
                .verify(token);
    }

    public String extractUsername(String token) {
        return verify(token).getSubject();
    }
}
