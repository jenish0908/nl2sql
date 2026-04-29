import json
from groq import Groq
from app.config import settings
from app.models.schemas import QueryIntent, ClarificationRequest, AgentUsage, IntentType

INTENT_SYSTEM_PROMPT = """You are an expert SQL analyst. Your job is to analyze natural language questions about a database and extract structured intent information.

The database is an e-commerce system with these tables:
- customers (id, name, email, city, signup_date, tier)
- products (id, name, category, price, cost, supplier_id, stock_quantity)
- orders (id, customer_id, order_date, status, total_amount, delivery_city)
- order_items (id, order_id, product_id, quantity, unit_price, discount_pct)
- suppliers (id, name, city, rating, lead_time_days)

You must respond with ONLY a valid JSON object (no markdown, no explanation):
{
  "intent_type": "aggregation" | "filter" | "join" | "trend" | "comparison",
  "entities": ["list of table or column names referenced"],
  "time_range": "extracted time filter or null",
  "ambiguity_flags": ["list of genuinely ambiguous things that would produce different SQL"]
}

Rules:
- intent_type: aggregation (SUM/COUNT/AVG), filter (WHERE conditions), join (multiple tables), trend (over time), comparison (comparing groups)
- entities: use snake_case table/column names from the schema above
- time_range: extract naturally (e.g. "last month", "last 7 days", "this year") or null
- ambiguity_flags: only flag things that would genuinely change the query — be conservative
- Respond ONLY with the JSON object, nothing else."""

_client = Groq(api_key=settings.groq_api_key)


def extract_intent(
    question: str,
) -> tuple[QueryIntent | ClarificationRequest, AgentUsage]:
    response = _client.chat.completions.create(
        model=settings.groq_model,
        max_tokens=512,
        temperature=0,
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}"},
        ],
    )

    usage = AgentUsage(
        input_tokens=response.usage.prompt_tokens,
        output_tokens=response.usage.completion_tokens,
        total_tokens=response.usage.total_tokens,
        cost_usd=0.0,
    )

    raw = response.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        import re
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group())
        else:
            data = {
                "intent_type": "filter",
                "entities": [],
                "time_range": None,
                "ambiguity_flags": ["Could not parse intent — please rephrase your question"],
            }

    ambiguity_flags = data.get("ambiguity_flags", [])
    if ambiguity_flags:
        return ClarificationRequest(
            original_question=question,
            clarification_needed=f"Please clarify: {'; '.join(ambiguity_flags)}",
            ambiguity_flags=ambiguity_flags,
        ), usage

    intent_type_raw = data.get("intent_type", "filter")
    try:
        intent_type = IntentType(intent_type_raw)
    except ValueError:
        intent_type = IntentType.filter

    intent = QueryIntent(
        intent_type=intent_type,
        entities=data.get("entities", []),
        time_range=data.get("time_range"),
        ambiguity_flags=[],
    )
    return intent, usage
