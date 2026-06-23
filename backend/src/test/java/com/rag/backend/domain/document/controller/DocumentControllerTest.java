package com.rag.backend.domain.document.controller;

import com.rag.backend.domain.document.service.DocumentService;
import com.rag.backend.global.config.SecurityConfig;
import com.rag.backend.global.security.CustomUserDetailsService;
import com.rag.backend.global.security.JwtAuthenticationFilter;
import com.rag.backend.global.security.JwtTokenProvider;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.boot.webmvc.test.autoconfigure.WebMvcTest;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Import;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.mock.web.MockMultipartFile;
import org.springframework.test.web.servlet.MockMvc;
import java.util.Collections;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;
import static org.springframework.security.test.web.servlet.request.SecurityMockMvcRequestPostProcessors.csrf;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.multipart;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

@WebMvcTest(DocumentController.class)
@Import(SecurityConfig.class)
class DocumentControllerTest {

    @Autowired
    private MockMvc mockMvc;

    @MockitoBean
    private DocumentService documentService;

    @MockitoBean
    private JwtTokenProvider jwtTokenProvider;

    @MockitoBean
    private CustomUserDetailsService customUserDetailsService;

    @TestConfiguration
    static class TestConfig {
        @Bean
        public FilterRegistrationBean<JwtAuthenticationFilter> jwtAuthenticationFilterRegistration(JwtAuthenticationFilter filter) {
            FilterRegistrationBean<JwtAuthenticationFilter> registration = new FilterRegistrationBean<>(filter);
            registration.setEnabled(false);
            return registration;
        }
    }

    @Test
    void uploadDocumentSuccess() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", "test.pdf", "application/pdf", "pdf content".getBytes()
        );
        given(jwtTokenProvider.validateToken(any())).willReturn(true);
        given(jwtTokenProvider.getEmail(any())).willReturn("user@test.com");
        given(customUserDetailsService.loadUserByUsername("user@test.com")).willReturn(
                new org.springframework.security.core.userdetails.User(
                        "user@test.com", "password", Collections.emptyList()
                )
        );
        given(documentService.uploadDocument(eq("user@test.com"), any())).willReturn(1L);

        mockMvc.perform(multipart("/api/documents")
                        .file(file)
                        .header("Authorization", "Bearer mock-token")
                        .with(csrf()))
                .andExpect(status().isOk());
    }

    @Test
    void uploadDocumentUnauthorized() throws Exception {
        MockMultipartFile file = new MockMultipartFile(
                "file", "test.pdf", "application/pdf", "pdf content".getBytes()
        );

        mockMvc.perform(multipart("/api/documents")
                        .file(file)
                        .with(csrf()))
                .andExpect(status().isForbidden());
    }
}
