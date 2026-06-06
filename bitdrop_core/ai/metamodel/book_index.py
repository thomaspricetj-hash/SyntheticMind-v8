# bitdrop_core/ai/metamodel/book_index.py

"""
Book-style index of all models in the system.
Each entry is a "page" in the book with chapter, role, and description.
"""

MODEL_BOOK = [
    {
        "name": "phi3:mini",
        "role": "narrator",
        "chapter": "talk",
        "intent": "talk",
        "summary": "Fast conversational model used as the primary voice.",
        "description": "Handles small talk, narration, light reasoning, and stitching other models' outputs together.",
    },
    {
        "name": "qwen2.5:1.5b",
        "role": "light_reasoning",
        "chapter": "light_reasoning",
        "intent": "light_reasoning",
        "summary": "Lightweight reasoning model.",
        "description": "Used for slightly more complex tasks than phi3, but still fast and efficient.",
    },
    {
        "name": "llama3.1:8b",
        "role": "general_reasoning",
        "chapter": "general_reasoning",
        "intent": "general_reasoning",
        "summary": "General-purpose reasoning model.",
        "description": "Handles medium-length, multi-step reasoning and explanation tasks.",
    },
    {
        "name": "qwen2.5:7b",
        "role": "deep_reasoning",
        "chapter": "deep_reasoning",
        "intent": "deep_reasoning",
        "summary": "Deep reasoning and escalation model.",
        "description": "Used when tasks are long, complex, or escalated from smaller models.",
    },
    {
        "name": "deepseek-coder:6.7b",
        "role": "code",
        "chapter": "code_reasoning",
        "intent": "code_reasoning",
        "summary": "Code-focused model.",
        "description": "Handles code generation, debugging, refactoring, and technical programming explanations.",
    },
    {
        "name": "deepseek-r1:7b",
        "role": "math",
        "chapter": "math_reasoning",
        "intent": "math_reasoning",
        "summary": "Math and logic model.",
        "description": "Used for equations, proofs, structured reasoning, and step-by-step problem solving.",
    },
    {
        "name": "qwen3-vl:8b",
        "role": "vision",
        "chapter": "vision_reasoning",
        "intent": "vision_reasoning",
        "summary": "Vision-language model.",
        "description": "Handles image understanding, OCR-like tasks, and visual question answering.",
    },
    {
        "name": "bge-large:latest",
        "role": "embedding",
        "chapter": "embed",
        "intent": "embed",
        "summary": "Embedding model.",
        "description": "Used for semantic search, memory indexing, and vector-based retrieval.",
    },
]
