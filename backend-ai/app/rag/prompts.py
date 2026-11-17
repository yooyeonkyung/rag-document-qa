from langchain_core.prompts import ChatPromptTemplate

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
        ("human", "{question}"),
    ]
)
