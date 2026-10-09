"""
dummy_ai_service.py
--------------------
Yeh ek TEMPORARY fake AI service hai.
Phase 11 mein hum is function ke andar ka code replace kar denge
Student 1 ke asli service call se.
"""

from backend.database.schemas import AIRequest, AIResponse, Source


def get_dummy_answer(request: AIRequest) -> AIResponse:
    """Dummy response mein received previous turns ka count batao."""
    previous_turns = len(request.history)
    return AIResponse(
        answer=(
            f"Temporary response for: '{request.message}' "
            f"(received {previous_turns} previous turns)"
        ),
        language="hinglish",
        sources=[
            Source(document="sample_document.pdf", page=1, section="Demo")
        ],
        confidence=1.0,
    )
