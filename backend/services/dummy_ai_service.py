"""Development/test-only dummy AI; never use this module for production AI logic."""

from backend.database.schemas import AIRequest, AIResponse, Source


def get_dummy_answer(request: AIRequest) -> AIResponse:
    """Return a deterministic development response for local testing only."""
    previous_turns = len(request.history)
    return AIResponse(
        answer=(
            f"Temporary response for: '{request.message}' "
            f"(received {previous_turns} previous turns)"
        ),
        language="hinglish",
        sources=[Source(document="sample_document.pdf", page=1, section="Demo")],
        confidence=1.0,
    )
