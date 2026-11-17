from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# Step 1 (only when there is chat history): turn a follow-up like
# "그거 삭제는?" into a standalone question ("S3 버킷 삭제 방법은?") so the
# vector search looks for the right thing.
CONDENSE_QUESTION_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Given the conversation so far and a follow-up question, rewrite the follow-up "
            "as a standalone question that can be understood without the conversation. "
            "Keep the same language as the follow-up. If it is already standalone, return it unchanged. "
            "Return ONLY the question, nothing else.",
        ),
        MessagesPlaceholder("history"),
        ("human", "Follow-up question: {question}"),
    ]
)

# Step 2: answer from the retrieved excerpts.
QA_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You answer questions about a document using ONLY the excerpts below.\n"
            "- If the excerpts don't contain the answer, say you couldn't find it in the document. Do not guess.\n"
            "- Answer in the same language as the question.\n"
            "- Cite the page numbers you used, like (p.12).\n\n"
            "Excerpts:\n{context}",
        ),
        MessagesPlaceholder("history"),
        ("human", "{question}"),
    ]
)
