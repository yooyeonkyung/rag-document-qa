package com.rag.backend.domain.user.service;

import com.rag.backend.domain.user.entity.User;
import com.rag.backend.domain.user.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;

   
}
