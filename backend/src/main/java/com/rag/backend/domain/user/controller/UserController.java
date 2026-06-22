package com.rag.backend.domain.user.controller;


import com.rag.backend.domain.user.dto.TokenResponse;
import com.rag.backend.domain.user.dto.UserLoginRequest;
import com.rag.backend.domain.user.dto.UserRegisterRequest;
import com.rag.backend.domain.user.service.UserService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
public class UserController {

    private final UserService userService;

    @PostMapping("/register")
    public ResponseEntity<String> register(@RequestBody UserRegisterRequest request) {
        Long userId = userService.register(request);
        return ResponseEntity.ok("회원가입 완료. 회원 번호 : " + userId);
    }

    @PostMapping("/login")
    public ResponseEntity<TokenResponse> login(@RequestBody UserLoginRequest request) {
        String token = userService.login(request);
        return ResponseEntity.ok(new TokenResponse(token));
    }
}
