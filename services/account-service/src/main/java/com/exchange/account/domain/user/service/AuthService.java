package com.exchange.account.domain.user.service;

import com.exchange.account.domain.account.entity.Account;
import com.exchange.account.domain.account.entity.AccountType;
import com.exchange.account.domain.account.repository.AccountRepository;
import com.exchange.account.domain.user.dto.AuthResponse;
import com.exchange.account.domain.user.dto.LoginRequest;
import com.exchange.account.domain.user.dto.SignUpRequest;
import com.exchange.account.domain.user.entity.User;
import com.exchange.account.domain.user.repository.UserRepository;
import com.exchange.account.security.JwtProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.UUID;

/**
 * 회원가입 + 로그인 서비스
 * 회원 생성 시 기본 CASH 계좌 자동 생성
 */
@Slf4j
@Service
@RequiredArgsConstructor
@Transactional
public class AuthService {

    private final UserRepository userRepository;
    private final AccountRepository accountRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtProvider jwtProvider;

    public AuthResponse signUp(SignUpRequest request) {
        if (userRepository.existsByUsername(request.getUsername())) {
            throw new IllegalArgumentException("이미 사용 중인 사용자명입니다: " + request.getUsername());
        }
        if (userRepository.existsByEmail(request.getEmail())) {
            throw new IllegalArgumentException("이미 사용 중인 이메일입니다.");
        }

        User user = User.builder()
                .username(request.getUsername())
                .password(passwordEncoder.encode(request.getPassword()))
                .email(request.getEmail())
                .fullName(request.getFullName())
                .build();
        User saved = userRepository.save(user);

        // 기본 현금 계좌 자동 생성
        Account account = Account.builder()
                .user(saved)
                .accountNumber(generateAccountNumber())
                .accountType(AccountType.CASH)
                .build();
        accountRepository.save(account);

        log.info("[회원가입] userId={}, username={}", saved.getId(), saved.getUsername());
        String token = jwtProvider.generateToken(saved);
        return AuthResponse.of(token, saved.getId(), saved.getUsername(), saved.getRole());
    }

    @Transactional(readOnly = true)
    public AuthResponse login(LoginRequest request) {
        User user = userRepository.findByUsername(request.getUsername())
                .orElseThrow(() -> new IllegalArgumentException("사용자를 찾을 수 없습니다."));

        if (!user.isEnabled()) {
            throw new IllegalStateException("비활성화된 계정입니다.");
        }
        if (!passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new IllegalArgumentException("비밀번호가 일치하지 않습니다.");
        }

        log.info("[로그인] userId={}, username={}", user.getId(), user.getUsername());
        String token = jwtProvider.generateToken(user);
        return AuthResponse.of(token, user.getId(), user.getUsername(), user.getRole());
    }

    private String generateAccountNumber() {
        // ACC + 8자리 UUID 앞부분
        return "ACC" + UUID.randomUUID().toString().replace("-", "").substring(0, 8).toUpperCase();
    }
}
