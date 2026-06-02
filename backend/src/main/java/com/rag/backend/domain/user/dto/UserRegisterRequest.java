package com.rag.backend.domain.user.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;

public record UserRegisterRequest(String email, String password, String name) {
}
