"""
Customer support agent built with LangGraph.

Workflow:  categorize -> analyze_sentiment -> (route) -> handle_technical | handle_billing | handle_general | escalate

- With an LLM key in .env the nodes call a language model (OpenAI, or any OpenAI-compatible API such as Groq).
- Without a key the same graph runs with simple keyword rules, so the project works out of the box.
"""
import logging
import os
import random
import re
from typing import Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

load_dotenv()
log = logging.getLogger("support-agent")

COMPANY = "WaveLink"
CATEGORIES = ("Technical", "Billing", "General")
SENTIMENTS = ("Positive", "Neutral", "Negative")


# ---------------------------------------------------------------- state
class State(TypedDict, total=False):
    query: str
    history: List[Dict[str, str]]  # earlier turns: [{"role": "user" | "bot", "text": "..."}]
    category: str
    sentiment: str
    response: str
    escalated: bool
    ticket: Optional[str]
    wants_human: bool  # the customer asked for a person


# ---------------------------------------------------------------- LLM (optional)
def _build_llm():
    key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not key:
        return None
    from langchain_openai import ChatOpenAI  # imported here so rules mode does not need it

    kwargs = {
        "api_key": key,
        "model": os.getenv("LLM_MODEL", "gpt-4o-mini"),
        "temperature": 0,
    }
    if os.getenv("LLM_BASE_URL"):  # e.g. https://api.groq.com/openai/v1
        kwargs["base_url"] = os.getenv("LLM_BASE_URL")
    return ChatOpenAI(**kwargs)


LLM = _build_llm()
MODE = "llm" if LLM else "rules"

SUPPORT_RULES = (
    f"You are the support assistant for {COMPANY}, a fictional home internet provider. "
    "Answer in 2 to 4 short sentences. Be polite and practical. "
    "Never invent account details, prices or policies. Never use placeholders such as [Your Name]. "
    "If you do not have the information, say what the customer can check or offer a human agent. "
    "Reply in the same language the customer writes in (English, Hindi or Hinglish)."
)


def ask_llm(system: str, user: str) -> Optional[str]:
    """Call the LLM. Returns None if there is no LLM or the call fails (the caller then uses the rules)."""
    if LLM is None:
        return None
    try:
        reply = LLM.invoke([("system", system), ("human", user)])
        return str(reply.content).strip()
    except Exception as exc:  # network error, bad key, rate limit ...
        log.warning("LLM call failed, using rule-based fallback: %s", exc)
        return None


def pick(text: str, options, default: str) -> str:
    """Find which option the model answered with (case-insensitive)."""
    lowered = text.lower()
    for option in options:
        if option.lower() in lowered:
            return option
    return default


# ---------------------------------------------------------------- rule-based fallback
TECH_WORDS = r"nahi chal|chal nahi|band ho|net nahi|speed kam|internet|wifi|wi-fi|router|modem|connection|connect|network|slow|speed|outage|error|login|log in|password|app\b|crash|bug|not working|doesn'?t work|reset|install|update"
BILLING_WORDS = r"paise|rasid|recharge|bill|billing|invoice|receipt|payment|pay\b|refund|charge|charged|price|pricing|plan|subscription|card|renew|cancel"
NEGATIVE_WORDS = (
    r"bahut bura|bekar|gussa|pareshan|tang aa|angry|terrible|worst|useless|frustrat|hate|unacceptable|disappointed|ridiculous|awful|fed up|scam|"
    r"not working|doesn'?t work|broken|keeps? (dropping|disconnecting|crashing|failing|cutting)|again and again|still not"
)
POSITIVE_WORDS = r"shukriya|dhanyavaad|badhiya|thanks|thank you|great|love|awesome|perfect|excellent|amazing|helpful|appreciate"


HUMAN_REQUEST = (
    r"\b(human|real person|live agent|human agent|representative|manager|insaan)\b|"
    r"\b(talk|speak|connect)( me)? (to|with) (a |an |the )?(someone|somebody|person|agent|human)\b"
)


def wants_human(query: str) -> bool:
    return bool(re.search(HUMAN_REQUEST, query.lower()))


def rule_category(query: str) -> str:
    q = query.lower()
    if re.search(BILLING_WORDS, q):
        return "Billing"
    if re.search(TECH_WORDS, q):
        return "Technical"
    return "General"


def rule_sentiment(query: str) -> str:
    q = query.lower()
    if re.search(NEGATIVE_WORDS, q):
        return "Negative"
    if re.search(POSITIVE_WORDS, q):
        return "Positive"
    return "Neutral"


RULE_REPLIES = {
    "Technical": (
        "Sorry you are having trouble. Let's try a few quick steps:\n"
        "1. Restart your router: unplug it for 30 seconds, then plug it back in.\n"
        "2. Check that all cables are firmly connected.\n"
        "3. Move closer to the router, or try a wired connection.\n"
        "If it still does not work, tell me the error message or the light colours you see and I will help further."
    ),
    "Billing": (
        "You can find your receipts in your account under Billing > Invoices, and a copy is emailed after every payment. "
        "If you cannot find one, send me the email address you signed up with and the month you need."
    ),
    "General": (
        "Thanks for reaching out! I can help with technical problems, billing questions and general information "
        f"about {COMPANY}. Could you tell me a little more about what you need?"
    ),
}


def rule_reply(state: State) -> str:
    q = state["query"].lower()
    category = state.get("category", "General")
    if category == "General":
        if re.search(r"hours|open|close|available|when", q):
            return (
                "Our chat assistant is available 24/7. Human agents are available from 8 am to 8 pm, "
                "Monday to Saturday. Is there anything else I can help with?"
            )
        if re.search(r"^(hi|hello|hey)\b", q):
            return f"Hello! Welcome to {COMPANY} support. How can I help you today?"
        if re.search(POSITIVE_WORDS, q):
            return "You are very welcome! Let me know if there is anything else I can help with."
    return RULE_REPLIES[category]


# ---------------------------------------------------------------- node functions
def _history_text(state: State) -> str:
    turns = state.get("history") or []
    return "\n".join(f"{'Customer' if t['role'] == 'user' else 'Assistant'}: {t['text']}" for t in turns[-6:])


def categorize(state: State) -> State:
    """Classify the query as Technical, Billing or General."""
    answer = ask_llm(
        "Classify the customer query into exactly one category: Technical, Billing or General. "
        "Reply with only the category name.",
        state["query"],
    )
    category = pick(answer, CATEGORIES, "General") if answer else rule_category(state["query"])
    return {"category": category, "wants_human": wants_human(state["query"])}


def analyze_sentiment(state: State) -> State:
    """Classify the sentiment as Positive, Neutral or Negative."""
    answer = ask_llm(
        "Classify the sentiment of the customer query as Positive, Neutral or Negative. "
        "Reply with only one word.",
        state["query"],
    )
    sentiment = pick(answer, SENTIMENTS, "Neutral") if answer else rule_sentiment(state["query"])
    return {"sentiment": sentiment}


def _handle(kind: str):
    def node(state: State) -> State:
        history = _history_text(state)
        prompt = f"Earlier conversation:\n{history}\n\n" if history else ""
        prompt += f"Customer query: {state['query']}"
        answer = ask_llm(f"{SUPPORT_RULES} This is a {kind} support question.", prompt)
        return {"response": answer or rule_reply(state), "escalated": False, "ticket": None}

    node.__name__ = f"handle_{kind.lower()}"
    return node


handle_technical = _handle("Technical")
handle_billing = _handle("Billing")
handle_general = _handle("General")


def escalate(state: State) -> State:
    """Hand the conversation to a human agent (the customer sounds upset, or asked for a person)."""
    ticket = f"WL-{random.randint(10000, 99999)}"
    if state.get("wants_human"):
        text = (
            f"Of course. I have connected you with a human agent (ticket {ticket}). "
            "They will reply shortly. You can add more details here while you wait."
        )
    else:
        text = (
            "I am sorry about the trouble. This looks important, so I have passed it to a human agent "
            f"(ticket {ticket}). They will contact you shortly. You can reply here to add more details."
        )
    return {"response": text, "escalated": True, "ticket": ticket}


def route_query(state: State) -> str:
    """A request for a person, or negative sentiment, goes to a human. Everything else goes to the matching handler."""
    if state.get("wants_human") or state["sentiment"] == "Negative":
        return "escalate"
    return {
        "Technical": "handle_technical",
        "Billing": "handle_billing",
    }.get(state["category"], "handle_general")


# ---------------------------------------------------------------- graph
workflow = StateGraph(State)
workflow.add_node("categorize", categorize)
workflow.add_node("analyze_sentiment", analyze_sentiment)
workflow.add_node("handle_technical", handle_technical)
workflow.add_node("handle_billing", handle_billing)
workflow.add_node("handle_general", handle_general)
workflow.add_node("escalate", escalate)

workflow.set_entry_point("categorize")
workflow.add_edge("categorize", "analyze_sentiment")
workflow.add_conditional_edges(
    "analyze_sentiment",
    route_query,
    {
        "handle_technical": "handle_technical",
        "handle_billing": "handle_billing",
        "handle_general": "handle_general",
        "escalate": "escalate",
    },
)
for end_node in ("handle_technical", "handle_billing", "handle_general", "escalate"):
    workflow.add_edge(end_node, END)

graph = workflow.compile()


def run_support(query: str, history: Optional[List[Dict[str, str]]] = None) -> Dict:
    """Run one customer query through the graph and return the fields the API sends to the chat UI."""
    result = graph.invoke({"query": query, "history": history or []})
    return {
        "text": result["response"],
        "category": result["category"],
        "sentiment": result["sentiment"],
        "escalated": bool(result.get("escalated")),
        "ticket": result.get("ticket"),
    }
