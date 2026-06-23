package com.rag.backend.domain.document.entity;

import com.rag.backend.domain.user.entity.User;
import com.rag.backend.global.common.BaseTimeEntity;
import jakarta.persistence.*;
import lombok.AccessLevel;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "documents")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class Document extends BaseTimeEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @Column(name = "file_name", nullable = false)
    private String fileName;

    @Column(name = "s3_url", nullable = false, columnDefinition = "TEXT")
    private String s3Url;

    @Column(name = "file_size", nullable = false)
    private Long fileSize;

    @Builder
    public Document(User user, String fileName, String s3Url, Long fileSize) {
        this.user = user;
        this.fileName = fileName;
        this.s3Url = s3Url;
        this.fileSize = fileSize;
    }
}
