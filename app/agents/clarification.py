from app.agents.intent_extraction import extract_intent
from app.models.schemas import QueryIntent, ClarificationRequest, AgentUsage


def refine_with_clarification(
    original_question: str,
    clarification: str,
) -> tuple[QueryIntent | ClarificationRequest, AgentUsage]:
    combined = f"{original_question}\n\nAdditional context: {clarification}"
    return extract_intent(combined)
