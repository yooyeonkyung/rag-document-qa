package com.rag.backend.domain.user.controller;

import tools.jackson.databind.ObjectMapper;
import com.rag.backend.domain.user.dto.UserRegisterRequest;
import com.rag.backend.domain.user.dto.UserLoginRequest;
import com.rag.backend.domain.user.service.UserService;
import com.rag.backend.global.error.exception.EmailDuplicateException;
import com.rag.backend.global.error.exception.LoginFailedException;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.BDDMockito.given;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.rag.backend.global.security.JwtTokenProvider;
import com.rag.backend.global.security.CustomUserDetailsService;

@WebMvcTest(UserController.class)
class UserControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @Autowired
    private ObjectMapper objectMapper;

    @MockitoBean
    private UserService userService;

    @MockitoBean
    private JwtTokenProvider jwtTokenProvider;

    @MockitoBean
    private CustomUserDetailsService customUserDetailsService;

    @Test
    @WithMockUser
    void registerSuccess() throws Exception {
        UserRegisterRequest request = new UserRegisterRequest("test@test.com", "password", "name");
        given(userService.register(any())).willReturn(1L);

        mockMvc.perform(post("/register")
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk());
    }

    @Test
    @WithMockUser
    void registerDuplicateEmail() throws Exception {
        UserRegisterRequest request = new UserRegisterRequest("test@test.com", "password", "name");
        given(userService.register(any())).willThrow(new EmailDuplicateException());

        mockMvc.perform(post("/register")
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("U001"))
                .andExpect(jsonPath("$.message").value("Email is Duplicated"));
    }

    @Test
    @WithMockUser
    void loginSuccess() throws Exception {
        UserLoginRequest request = new UserLoginRequest("test@test.com", "password");
        given(userService.login(any())).willReturn("mock-jwt-token");

        mockMvc.perform(post("/login")
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").value("mock-jwt-token"));
    }

    @Test
    @WithMockUser
    void loginFailed() throws Exception {
        UserLoginRequest request = new UserLoginRequest("test@test.com", "password");
        given(userService.login(any())).willThrow(new LoginFailedException());

        mockMvc.perform(post("/login")
                        .with(csrf())
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(objectMapper.writeValueAsString(request)))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("U002"))
                .andExpect(jsonPath("$.message").value("Invalid email or password"));
    }
}
