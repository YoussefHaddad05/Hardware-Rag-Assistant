import ollama
from app.core.config import settings


def generate_rag_answer(question: str, context: str) -> str:
    """Passes the retrieved context and user question to the local LLM."""

    prompt = f"""Answer the user's question using ONLY information explicitly stated in the provided context.

STRICT GROUNDING RULES:
1. Do not use outside knowledge or your pretrained knowledge.
2. Do not make inferences or assumptions.
3. Do not combine separate clues to derive an answer that is not explicitly stated.
4. If the context only partially supports an answer, do not complete the missing information yourself.
5. Only answer with information that is directly and explicitly supported by the context.
6. If the answer is not explicitly stated in the context, say exactly:
"I don't know based on the provided documents."
7. Only include information that is directly relevant to the user's question.

CRITICAL CITATION INSTRUCTION:
Every factual statement must have an inline citation containing the source filename, page number, and chunk ID.
Do not add conversational filler, polite closing sentences, or general advice that lacks a citation. Every single sentence in your answer must end with an inline citation, or state the exact refusal phrase.

Citation format:
[filename | Page: X | Chunk: Y]

If the context does not explicitly support the answer, do not try to answer from your own knowledge.

Context:
{context}

Question:
{question}

Answer:"""

    response = ollama.generate(
        model=settings.LLM_MODEL,
        prompt=prompt
    )

    return response['response']