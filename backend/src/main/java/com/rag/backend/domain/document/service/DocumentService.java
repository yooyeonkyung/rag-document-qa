package com.rag.backend.domain.document.service;

import com.rag.backend.domain.document.entity.Document;
import com.rag.backend.domain.document.repository.DocumentRepository;
import com.rag.backend.domain.user.entity.User;
import com.rag.backend.domain.user.repository.UserRepository;
import com.rag.backend.global.common.S3UploadService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class DocumentService {

    private final DocumentRepository documentRepository;
    private final UserRepository userRepository;
    private final S3UploadService s3UploadService;

    @Transactional
    public Long uploadDocument(String email, MultipartFile file) throws IOException {
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new UsernameNotFoundException("User not found with email: " + email));

        String s3Url = s3UploadService.upload(file);

        Document document = Document.builder()
                .user(user)
                .fileName(file.getOriginalFilename())
                .s3Url(s3Url)
                .fileSize(file.getSize())
                .build();

        return documentRepository.save(document).getId();
    }
}
