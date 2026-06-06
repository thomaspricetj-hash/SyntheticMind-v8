from __future__ import annotations
from typing import Any, Dict, List, Optional
import json


# ============================================================
# Base helper interface (optional, for consistency)
# ============================================================
class BaseHelper:
    name: str = "BaseHelper"
    preferred_device: str = "cpu"

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


# ============================================================
# MemoryWriterHelperV1 (max-updated)
# ============================================================
class MemoryWriterHelperV1(BaseHelper):
    name = "MemoryWriterHelper"

    def __init__(self, memory) -> None:
        self.memory = memory
        self.preferred_device = "cpu"

    def run(
        self,
        query: str,
        answer: str,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Simple episodic memory writer:
        • Stores (query, answer, metadata) as an episodic record.
        • Designed to be extended later with extraction/embedding.
        """
        metadata = metadata or {}
        record = {
            "query": query,
            "answer": answer,
            "metadata": metadata,
        }

        try:
            if hasattr(self.memory, "store_episode"):
                self.memory.store_episode(record)
            elif hasattr(self.memory, "store"):
                self.memory.store(record)
        except Exception as e:
            return {"status": "error", "error": str(e), "record": record}

        return {"status": "stored", "record": record}


# ============================================================
# ChainOfThoughtHelperV1 (max-updated)
# ============================================================
class ChainOfThoughtHelperV1(BaseHelper):
    name = "ChainOfThoughtHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-cot-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        prompt = (
            "You are a reasoning engine. For the following question, produce a clear, "
            "step-by-step chain of thought before giving a final answer.\n\n"
            f"Question: {query}\n\n"
            "First, reason step by step. Then, at the end, write:\n"
            "\"Final answer: <your concise answer>\""
        )

        request = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.3,
        }

        try:
            text = self.llm_engine.generate(request)
        except Exception as e:
            return {"error": str(e), "cot": "", "final": ""}

        final_answer = ""
        marker = "Final answer:"
        if marker in text:
            final_answer = text.split(marker, 1)[1].strip()

        return {
            "cot": text,
            "final": final_answer,
        }


# ============================================================
# VerificationHelperV1 (max-updated)
# ============================================================
class VerificationHelperV1(BaseHelper):
    name = "VerificationHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-verifier-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"

    def run(
        self,
        query: str,
        answer: str,
        **kwargs,
    ) -> Dict[str, Any]:
        prompt = (
            "You are a strict verification engine.\n\n"
            f"Question: {query}\n"
            f"Proposed answer: {answer}\n\n"
            "Tasks:\n"
            "1. Check if the answer is logically consistent with the question.\n"
            "2. Check for obvious factual errors.\n"
            "3. Rate confidence from 0.0 to 1.0.\n"
            "4. If there are issues, propose a corrected answer.\n\n"
            "Respond in JSON with keys: consistent (bool), confidence (float), "
            "issues (list of strings), corrected_answer (string)."
        )

        request = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.1,
        }

        try:
            text = self.llm_engine.generate(request)
        except Exception as e:
            return {
                "consistent": False,
                "confidence": 0.0,
                "issues": [f"Verifier error: {e}"],
                "corrected_answer": answer,
            }

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Verifier output not a dict")
        except Exception:
            data = {
                "consistent": True,
                "confidence": 0.6,
                "issues": ["Verifier output not parseable; assuming partial consistency."],
                "corrected_answer": answer,
            }

        data.setdefault("consistent", True)
        data.setdefault("confidence", 0.5)
        data.setdefault("issues", [])
        data.setdefault("corrected_answer", answer)

        return data


# ============================================================
# TaskPlannerHelperV1 (max-updated)
# ============================================================
class TaskPlannerHelperV1(BaseHelper):
    name = "TaskPlannerHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-planner-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"

    def run(self, goal: str, **kwargs) -> Dict[str, Any]:
        prompt = (
            "You are a task planning engine.\n\n"
            f"Goal: {goal}\n\n"
            "Break this goal into a numbered list of concrete steps. "
            "Each step should be a short, actionable instruction.\n"
            "Then provide a short summary of the overall plan.\n\n"
            "Respond in JSON with keys: steps (list of strings), summary (string)."
        )

        request = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 512,
            "temperature": 0.4,
        }

        try:
            text = self.llm_engine.generate(request)
        except Exception as e:
            return {
                "steps": [],
                "summary": f"Planner error: {e}",
            }

        try:
            data = json.loads(text)
            if not isinstance(data, dict):
                raise ValueError("Planner output not a dict")
        except Exception:
            data = {
                "steps": [],
                "summary": "Planner output not parseable; no structured steps available.",
            }

        data.setdefault("steps", [])
        data.setdefault("summary", "")
        return data


# ============================================================
# DomainExpertRouterHelperV1 (multi-domain, max-updated)
# ============================================================
class DomainExpertRouterHelperV1(BaseHelper):
    name = "DomainExpertRouterHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-domain-expert-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"

        self.domains: Dict[str, Dict[str, Any]] = {
            "finance": {
                "keywords": ["interest", "loan", "mortgage", "roi", "investment", "npv", "irr"],
                "role": "You are a finance and investment expert.",
            },
            "legal": {
                "keywords": ["contract", "clause", "agreement", "liability", "jurisdiction", "nda"],
                "role": "You are a legal reasoning assistant (not a lawyer).",
            },
            "medical": {
                "keywords": ["symptom", "diagnosis", "treatment", "dose", "mg", "side effect"],
                "role": "You are a cautious medical information assistant (not a doctor).",
            },
            "chemistry": {
                "keywords": ["reaction", "mole", "stoichiometry", "bond", "acid", "base", "ph"],
                "role": "You are a chemistry expert.",
            },
            "biology": {
                "keywords": ["cell", "dna", "rna", "protein", "enzyme", "organism", "gene"],
                "role": "You are a biology and life sciences expert.",
            },
            "cybersecurity": {
                "keywords": ["exploit", "vulnerability", "cve", "xss", "sql injection", "rce"],
                "role": "You are a cybersecurity analyst. Do not provide exploit code.",
            },
            "data_science": {
                "keywords": ["regression", "classification", "dataset", "distribution", "p-value", "anova"],
                "role": "You are a data science and statistics expert.",
            },
            "design": {
                "keywords": ["ui", "ux", "layout", "wireframe", "design system", "typography"],
                "role": "You are a design and UX expert.",
            },
            "story": {
                "keywords": ["plot", "character", "story", "narrative", "arc", "scene"],
                "role": "You are a story structure and narrative expert.",
            },
            "brainstorm": {
                "keywords": ["ideas", "brainstorm", "concepts", "options", "alternatives"],
                "role": "You are a creative brainstorming assistant.",
            },
        }

    def _detect_domain(self, query: str) -> str:
        q_lower = query.lower()
        best_domain = "general"
        best_score = 0

        for domain, cfg in self.domains.items():
            score = sum(1 for kw in cfg["keywords"] if kw in q_lower)
            if score > best_score:
                best_score = score
                best_domain = domain

        return best_domain

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        domain = self._detect_domain(query)
        cfg = self.domains.get(domain)

        if cfg is None:
            role = "You are a knowledgeable general reasoning assistant."
        else:
            role = cfg["role"]

        prompt = (
            f"{role}\n\n"
            f"User question (domain: {domain}):\n{query}\n\n"
            "Provide a clear, structured answer. If the question is safety-sensitive, "
            "respond cautiously and avoid giving harmful instructions."
        )

        request = {
            "model": self.model_name,
            "prompt": prompt,
            "max_tokens": 768,
            "temperature": 0.5,
        }

        try:
            answer = self.llm_engine.generate(request)
        except Exception as e:
            return {
                "domain": domain,
                "answer": f"Domain expert error: {e}",
            }

        return {
            "domain": domain,
            "answer": answer,
        }

