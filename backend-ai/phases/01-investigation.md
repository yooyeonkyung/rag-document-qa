# Phase 1 — Investigating what Spring Boot actually outputs

Before writing any code, the goal was to find out exactly what the existing
Spring Boot backend (written by a teammate) returns when a document is
uploaded, since that output is the only thing this service has to work
with.

## What was found

**Endpoint**: `POST /api/documents` in
`backend/src/main/java/com/rag/backend/domain/document/controller/DocumentController.java`

```java
@PostMapping
public ResponseEntity<Long> uploadDocument(
        @RequestParam("file") MultipartFile file,
        @AuthenticationPrincipal UserDetails userDetails) throws IOException {
    Long documentId = documentService.uploadDocument(userDetails.getUsername(), file);
    return ResponseEntity.ok(documentId);
}
```

- Requires `Authorization: Bearer <jwt>`.
- The response body is a **bare JSON number** (the new document's id) — not
  `{"id": 42}`, just `42`. There is no DTO wrapping it.
- `DocumentService.uploadDocument()` uploads the file to S3
  (`S3UploadService`) and saves a `Document` row (`fileName`, `s3Url`,
  `fileSize`) — but none of that is returned to the caller. It only lives in
  MySQL.
- There is no `GET /api/documents/{id}` endpoint, and no mechanism (event,
  webhook, outbound call) wiring Spring to this service. Nothing calls
  FastAPI automatically today.

**JWT**: `JwtTokenProvider` signs tokens with
`Keys.hmacShaKeyFor(Base64.decode(jwt.secret))`, algorithm `HS256`, and the
only claim is `sub` = the user's email. No roles, no user id. This matters
because it's the only identity FastAPI can trust without its own login
system — see Phase 2.

**Dependency stack**: `README.md` states the AI backend should use the
OpenAI API, but `test/requirements.txt` (a prior scratch venv) only has
`langchain-groq` and `langchain-google-genai` installed — no `openai`
package. This discrepancy was raised with the project owner, who chose
**Google Gemini** for the LLM work that will happen in `ai/ai_core` later.
Not directly relevant to this service (see Phase 2), but recorded here
since it came out of the same investigation.

## Conclusion this phase led to

Spring's real output today is just an integer id — not enough on its own
for anything to fetch the file. Whatever bridges Spring and LangChain needs
the S3 url too, which isn't in the response yet. That gap is tracked in
Phase 3 rather than worked around by guessing.
