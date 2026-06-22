package com.rag.backend.global.error.exception;

import com.rag.backend.global.error.ErrorCode;

public class LoginFailedException extends BusinessException {
    public LoginFailedException() {
        super(ErrorCode.LOGIN_FAILED);
    }
}
