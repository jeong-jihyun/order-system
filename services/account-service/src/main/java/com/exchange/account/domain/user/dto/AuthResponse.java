package com.exchange.account.domain.user.dto;

import com.exchange.account.domain.user.entity.UserRole;
import lombok.Builder;
import lombok.Getter;

@Getter
@Builder
public class AuthResponse {
    private String accessToken;
    private String tokenType;
    private Long userId;
    private String username;
    private UserRole role;
    private long expiresIn; // 초 단위

    public static AuthResponse of(String token, Long userId, String username, UserRole role) {
        return AuthResponse.builder()
                .accessToken(token)
                .tokenType("Bearer")
                .userId(userId)
                .username(username)
                .role(role)
                .expiresIn(86400L) // 24시간
                .build();
    }
}
