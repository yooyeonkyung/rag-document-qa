# RAG golden evaluation set (DRAFT)

> **Status: draft, pending human review.** The answer pages and reference answers were checked against text extracted from the PDF, but a person should confirm them before using the scores.

`golden_set.jsonl` holds 25 question/answer pairs for evaluating the RAG pipeline on a single document.

## Source and page range

- Document: `file/s3-userguide.pdf` (Amazon S3 User Guide, English).
- Indexed range: **pages 26-125 (inclusive)**. Every answerable question is answered within this range.
- Page numbers are **1-based pypdf indices**: page N is `PdfReader(path).pages[N-1]`. These are *not* the page numbers printed in the PDF footer. For example, pypdf page 26 is printed page 1 ("What is Amazon S3?").

## Format

Each line is one JSON object with these fields:

| Field | Meaning |
|---|---|
| `id` | `q01` to `q25` |
| `question` | A user-style question in English |
| `type` | `factual` (a single fact), `procedural` (steps), `multi_page` (the answer needs 2 or more pages), or `unanswerable` (not answered anywhere in pages 26-125) |
| `answer_pages` | The minimal list of 1-based pypdf pages that contain the answer. `[]` for unanswerable questions |
| `reference_answer` | A 1-3 sentence correct answer grounded in those pages. `"Not in the document."` for unanswerable questions |
| `evidence` | A short verbatim quote (25 words or fewer) from the main answer page, for quick checking. `""` for unanswerable questions |
| `notes` | Points for the reviewer: alternative pages, distractor pages, or caveats. May be empty |

Some content appears twice in the range. For example, the console "create bucket" steps are on pages 48-54 and again on 121-125. In those cases `answer_pages` lists every page that fully answers the question, and the `notes` field says that either page is enough. When you score retrieval, count a hit on any listed page.

The evidence quotes come from pypdf text. The PDF uses ligature characters (for example "ﬁ"), and the quotes spell these as plain letters ("fi").

## Type counts

| Type | Count |
|---|---|
| factual | 9 |
| procedural | 7 |
| multi_page | 4 |
| unanswerable | 5 |
| **total** | **25** |

For each unanswerable question, pages 26-125 were searched for its key terms to confirm the answer is absent. The terms searched and any nearby distractor pages are listed in `notes`.
