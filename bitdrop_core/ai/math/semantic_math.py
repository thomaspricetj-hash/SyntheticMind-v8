from __future__ import annotations
from .symbolic import Expr

# We embed using the MathEngine's UniversalAI skimmer.
# The MathEngine will inject the correct embedding function at runtime.
# These functions are thin wrappers that defer to the engine.

def embed_math_text(text: str):
    """
    Embed raw math text using the MathEngine's deterministic embedding.
    The MathEngine will patch this function at runtime.
    """
    from .math_engine import MathEngine
    engine = MathEngine()
    return engine.ua.skimmer.embed(text)


def embed_expr(expr: Expr):
    """
    Embed a symbolic expression by converting it to string first.
    """
    return embed_math_text(str(expr))

