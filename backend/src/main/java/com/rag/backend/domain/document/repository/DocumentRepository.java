package com.rag.backend.domain.document.repository;

import com.rag.backend.domain.document.entity.Document;
import org.springframework.data.jpa.repository.JpaRepository;

public interface DocumentRepository extends JpaRepository<Document, Long> {
}
