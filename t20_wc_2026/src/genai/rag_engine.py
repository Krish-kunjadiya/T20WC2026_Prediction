"""
RAG Engine using:
  - ChromaDB  : vector similarity retrieval
  - Gemini AI : answer generation (google-generativeai)
"""

import os
import logging
from typing import Dict, List, Optional

import chromadb
import google.generativeai as genai
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "chromadb")

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DEFAULT_MODEL_CANDIDATES = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]

SYSTEM_PROMPT = """You are CricAI, an expert T20 cricket analyst and
commentator for the ICC T20 World Cup 2026. You have deep knowledge of:
- Player statistics and performance history
- Team strengths, weaknesses, and strategies
- Venue conditions and pitch behavior
- Match outcomes and tournament history
- T20 cricket tactics and game analysis

Answer questions using the provided context from the cricket database.
Be specific, insightful, and use cricket terminology naturally.
If the context doesn't contain enough information, use your general
cricket knowledge but mention it's based on general knowledge.
Keep responses concise (2-4 sentences) unless asked for detail.
"""


def _resolve_model_name() -> str:
    """Resolve an available Gemini model, preferring flash variants."""
    env_model = os.getenv("GEMINI_MODEL")
    if env_model:
        return env_model

    try:
        available = []
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", []) or []
            if "generateContent" in methods:
                available.append(getattr(m, "name", ""))

        normalized = {name.replace("models/", "") for name in available}
        for candidate in DEFAULT_MODEL_CANDIDATES:
            if candidate in normalized:
                return candidate

        for name in normalized:
            if "flash" in name:
                return name
        if normalized:
            return sorted(normalized)[0]
    except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
        logger.warning("Gemini model discovery failed, using fallback: %s", exc)

    return DEFAULT_MODEL_CANDIDATES[-1]


GEMINI_MODEL = _resolve_model_name()


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    ef = embedding_functions.DefaultEmbeddingFunction()
    return client.get_or_create_collection(name="cricket_knowledge", embedding_function=ef)


def retrieve_context(query: str, n_results: int = 5) -> str:
    """Retrieve relevant documents from ChromaDB."""
    try:
        collection = get_collection()
        count = collection.count()
        if count == 0:
            return "No knowledge base found. Please run knowledge_base.py first."
        results = collection.query(query_texts=[query], n_results=min(n_results, count))
        docs = results.get("documents", [[]])[0]
        return "\n\n".join([f"[{i + 1}] {doc}" for i, doc in enumerate(docs)])
    except Exception as exc:
        return f"Context retrieval error: {exc}"


def _format_history(history: List[Dict]) -> str:
    if not history:
        return "No previous messages."
    lines: List[str] = []
    for msg in history[-4:]:
        role = "User" if msg.get("role") == "user" else "CricAI"
        lines.append(f"{role}: {msg.get('content', '')}")
    return "\n".join(lines)


def ask_cricai(question: str, chat_history: Optional[List[Dict]] = None) -> str:
    """
    Full RAG pipeline:
    1. Retrieve relevant context from ChromaDB
    2. Build augmented prompt
    3. Generate answer with Gemini
    """
    context = retrieve_context(question, n_results=5)

    augmented_prompt = f"""
{SYSTEM_PROMPT}

RETRIEVED CONTEXT FROM CRICKET DATABASE:
{context}

CHAT HISTORY:
{_format_history(chat_history or [])}

USER QUESTION: {question}

Answer based on the context above. Be a helpful cricket expert:"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(augmented_prompt)
        text = getattr(response, "text", "") or ""
        return text.strip() if text else "No response text returned by Gemini."
    except Exception as exc:
        return f"Gemini error: {exc}"


def generate_match_preview(team_a: str, team_b: str, venue: str = "neutral") -> str:
    """Generate AI pre-match preview using team data + Gemini."""
    context_a = retrieve_context(f"{team_a} cricket statistics performance", 3)
    context_b = retrieve_context(f"{team_b} cricket statistics performance", 3)
    venue_ctx = retrieve_context(f"{venue} cricket venue pitch conditions", 2)

    prompt = f"""
{SYSTEM_PROMPT}

TEAM A DATA ({team_a}):
{context_a}

TEAM B DATA ({team_b}):
{context_b}

VENUE DATA:
{venue_ctx}

Generate a compelling 3-paragraph pre-match preview for:
{team_a} vs {team_b} at {venue}

Structure:
Paragraph 1: Team form and recent performance comparison
Paragraph 2: Key player matchups and tactical analysis
Paragraph 3: Prediction with reasoning

Write like a professional cricket analyst:"""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = getattr(response, "text", "") or ""
        return text.strip() if text else "No response text returned by Gemini."
    except Exception as exc:
        return f"Preview generation error: {exc}"


if __name__ == "__main__":
    print("Testing CricAI RAG Engine...\n")
    test_questions = [
        "Who are the top run scorers in this tournament?",
        "Which team has the best death over bowling?",
        "What is India's win rate?",
    ]
    for q in test_questions:
        print(f"Q: {q}")
        print(f"A: {ask_cricai(q)}\n")
