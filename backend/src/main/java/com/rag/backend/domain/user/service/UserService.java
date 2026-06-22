package com.rag.backend.domain.user.service;

import com.rag.backend.domain.user.dto.UserRegisterRequest;
import com.rag.backend.domain.user.entity.User;
import com.rag.backend.domain.user.repository.UserRepository;
import com.rag.backend.global.error.exception.EmailDuplicateException;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserService {
    private final UserRepository userRepository;

    @Transactional
    public Long register(UserRegisterRequest request) {
        if(userRepository.existsByEmail(request.email())) {
            throw new EmailDuplicateException();
        }

        User user = User.builder()
                .email(request.email())
                .password(request.password())
                .name(request.name())
                .build();

        return userRepository.save(user).getId();
    }
}
