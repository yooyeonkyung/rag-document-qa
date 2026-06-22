package com.rag.backend.global.error.exception;

import com.rag.backend.global.error.ErrorCode;

public class EmailDuplicateException extends BusinessException {
    public EmailDuplicateException() {
        super(ErrorCode.EMAIL_DUPLICATION);
    }
}
