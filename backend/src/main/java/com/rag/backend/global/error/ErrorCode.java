package com.rag.backend.global.error;

import lombok.Getter;

@Getter
public enum ErrorCode {
    INVALID_INPUT_VALUE(400, "C001", "Invalid Input Value"),
    INTERNAL_SERVER_ERROR(500, "C002", "Server Error"),
    EMAIL_DUPLICATION(400, "U001", "Email is Duplicated"),
    LOGIN_FAILED(400, "U002", "Invalid email or password");

    private final int status;
    private final String code;
    private final String message;

    ErrorCode(int status, String code, String message) {
        this.status = status;
        this.code = code;
        this.message = message;
    }
}
