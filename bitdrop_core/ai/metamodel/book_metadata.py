# bitdrop_core/ai/metamodel/book_metadata.py

from typing import List, Dict, Optional
from .book_index import MODEL_BOOK


def get_all_pages() -> List[Dict]:
    return MODEL_BOOK


def find_by_role(role: str) -> Optional[Dict]:
    for page in MODEL_BOOK:
        if page.get("role") == role:
            return page
    return None


def find_by_intent(intent: str) -> Optional[Dict]:
    for page in MODEL_BOOK:
        if page.get("intent") == intent:
            return page
    return None


def describe_book() -> str:
    lines = []
    for page in MODEL_BOOK:
        lines.append(
            f"- {page['name']} ({page['role']} / {page['chapter']}): {page['summary']}"
        )
    return "\n".join(lines)
