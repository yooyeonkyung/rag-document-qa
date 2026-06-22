package com.rag.backend.domain.user.service;

import com.rag.backend.domain.user.dto.UserLoginRequest;
import com.rag.backend.domain.user.dto.UserRegisterRequest;
import com.rag.backend.domain.user.entity.User;
import com.rag.backend.domain.user.repository.UserRepository;
import com.rag.backend.global.error.exception.EmailDuplicateException;
import com.rag.backend.global.error.exception.LoginFailedException;
import com.rag.backend.global.security.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserService {
    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider jwtTokenProvider;

    @Transactional
    public Long register(UserRegisterRequest request) {
        if(userRepository.existsByEmail(request.email())) {
            throw new EmailDuplicateException();
        }

        User user = User.builder()
                .email(request.email())
                .password(passwordEncoder.encode(request.password()))
                .name(request.name())
                .build();

        return userRepository.save(user).getId();
    }

    public String login(UserLoginRequest request) {
        User user = userRepository.findByEmail(request.email())
                .orElseThrow(LoginFailedException::new);

        if (!passwordEncoder.matches(request.password(), user.getPassword())) {
            throw new LoginFailedException();
        }

        return jwtTokenProvider.createToken(user.getEmail());
    }
}
