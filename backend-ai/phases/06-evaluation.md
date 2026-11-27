# Phase 6 — Evaluation

## Decisions (project owner, 2026-11-23)

- **Golden set:** Claude drafts ~25 English questions with answer pages
  (incl. unanswerable ones); the project owner reviews and edits them.
  Chosen over LLM-generated synthetic questions: no LLM quota needed, and
  "human-reviewed golden set" is more trustworthy.
- **Metrics are implemented by the project owner first**, to understand
  them: Recall@k, Hit@k, MRR, answer correctness, faithfulness (grounded in
  retrieved chunks / hallucination), context relevance, and "not in the
  document" handling for unanswerable questions. RAGAS comes afterwards
  for practical tool experience.
- Use the results to compare settings and pick the embedding model (Gemini
  vs local models such as BGE-M3), chunk size and k.

## Golden set (draft, pending review)

`eval/golden_set.jsonl` + `eval/README.md`.
- Source: pages 26-125 of `file/s3-userguide.pdf` (pypdf 1-based numbering;
  page 26 = printed page 1 "What is Amazon S3?"). Index exactly this range
  before evaluating:
  `python -m scripts.try_rag ../file/s3-userguide.pdf --pages 26-125 --document-id 100 --index-only`
- 25 questions: 9 factual, 7 procedural, 4 multi_page, 5 unanswerable.
- Each answerable question has `answer_pages`, a `reference_answer` and a
  verbatim `evidence` quote (checked by script to appear on the page).
- Unanswerable questions were checked by searching the range for their key
  terms (recorded in `notes`).
- Some answers appear on two pages (e.g. q08, q17): a retrieval hit on any
  listed page counts.
- Topics where the PDF contradicts itself (number of partitions, Storage
  Lens metric count) were avoided.

## Cost notes (Gemini free tier)

- Retrieval metrics (Recall/Hit/MRR) need only embeddings (one per
  question) - cheap, can run often.
- Answer metrics need the chat model, and LLM-as-judge needs extra calls per
  question; with 20 Flash requests/day this means a few questions per day
  on the free tier - a reason to revisit the paid tier at that point.

## Next

1. Project owner reviews the golden set.
2. Project owner implements retrieval metrics (with guidance), then answer
   metrics; Claude provides the runner scaffolding and reviews.
3. Experiments, then RAGAS.
