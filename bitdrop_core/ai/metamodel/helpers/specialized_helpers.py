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

from typing import Any, Dict, List, Optional
import json
import zlib


# ============================================================
# MICRO HELPERS (SHARED)
# ============================================================
class MicroStringStripper:
    __slots__ = ()

    @staticmethod
    def clean(text: str) -> str:
        return " ".join((text or "").split())


class MicroTokenLimiter:
    __slots__ = ()

    @staticmethod
    def limit(text: str, max_chars: int = 8000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroFastHash:
    __slots__ = ()

    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


# ============================================================
# Base helper interface (optional, for consistency)
# ============================================================
class BaseHelper:
    name: str = "BaseHelper"
    preferred_device: str = "cpu"

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError


# ============================================================
# MemoryWriterHelperV1 (max-updated + 3D)
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


class MemoryWriterHelper3D(BaseHelper):
    name = "MemoryWriterHelper3D"

    def __init__(self, memory) -> None:
        self.helper = MemoryWriterHelperV1(memory)
        self.preferred_device = "cpu"

    def run_3d(
        self,
        queries_3d: List[List[List[str]]],
        answers_3d: List[List[List[str]]],
        metadata_3d: Optional[List[List[List[Dict[str, Any]]]]] = None,
        **kwargs,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane_q = queries_3d[d]
            plane_a = answers_3d[d]
            plane_m = metadata_3d[d] if metadata_3d is not None else None

            plane_out: List[List[Dict[str, Any]]] = []
            for r_idx, row_q in enumerate(plane_q):
                row_a = plane_a[r_idx]
                row_m = plane_m[r_idx] if plane_m is not None else None

                row_out: List[Dict[str, Any]] = []
                for c_idx, q in enumerate(row_q):
                    a = row_a[c_idx]
                    m = row_m[c_idx] if row_m is not None else None
                    row_out.append(
                        self.helper.run(
                            query=q,
                            answer=a,
                            metadata=m,
                            **kwargs,
                        )
                    )
                plane_out.append(row_out)
            out.append(plane_out)

        return out


# ============================================================
# ChainOfThoughtHelperV1 (max-updated + cache + 3D)
# ============================================================
class ChainOfThoughtHelperV1(BaseHelper):
    name = "ChainOfThoughtHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-cot-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"
        self.cache: Dict[int, Dict[str, Any]] = {}

    def run(self, query: str, **kwargs) -> Dict[str, Any]:
        query = MicroStringStripper.clean(query)
        query = MicroTokenLimiter.limit(query)
        if not query:
            return {"cot": "", "final": ""}

        h = MicroFastHash.h(query)
        cached = self.cache.get(h)
        if cached is not None:
            return cached

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
            env = {"error": str(e), "cot": "", "final": ""}
            self.cache[h] = env
            return env

        final_answer = ""
        marker = "Final answer:"
        if marker in text:
            final_answer = text.split(marker, 1)[1].strip()

        env = {
            "cot": text,
            "final": final_answer,
        }
        self.cache[h] = env
        return env


class ChainOfThoughtHelper3D(BaseHelper):
    name = "ChainOfThoughtHelper3D"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-cot-v1") -> None:
        self.helper = ChainOfThoughtHelperV1(llm_engine, model_name)
        self.preferred_device = "gpu"

    def run_3d(
        self,
        queries_3d: List[List[List[str]]],
        **kwargs,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    row_out.append(self.helper.run(q, **kwargs))
                plane_out.append(row_out)
            out.append(plane_out)

        return out


# ============================================================
# VerificationHelperV1 (max-updated + cache + 3D)
# ============================================================
class VerificationHelperV1(BaseHelper):
    name = "VerificationHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-verifier-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"
        self.cache: Dict[int, Dict[str, Any]] = {}

    def run(
        self,
        query: str,
        answer: str,
        **kwargs,
    ) -> Dict[str, Any]:
        query = MicroStringStripper.clean(query)
        answer = MicroStringStripper.clean(answer)
        query = MicroTokenLimiter.limit(query)
        answer = MicroTokenLimiter.limit(answer)

        key = f"{query}|||{answer}"
        h = MicroFastHash.h(key)
        cached = self.cache.get(h)
        if cached is not None:
            return cached

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
            env = {
                "consistent": False,
                "confidence": 0.0,
                "issues": [f"Verifier error: {e}"],
                "corrected_answer": answer,
            }
            self.cache[h] = env
            return env

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

        self.cache[h] = data
        return data


class VerificationHelper3D(BaseHelper):
    name = "VerificationHelper3D"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-verifier-v1") -> None:
        self.helper = VerificationHelperV1(llm_engine, model_name)
        self.preferred_device = "gpu"

    def run_3d(
        self,
        queries_3d: List[List[List[str]]],
        answers_3d: List[List[List[str]]],
        **kwargs,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane_q = queries_3d[d]
            plane_a = answers_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for r_idx, row_q in enumerate(plane_q):
                row_a = plane_a[r_idx]
                row_out: List[Dict[str, Any]] = []
                for c_idx, q in enumerate(row_q):
                    a = row_a[c_idx]
                    row_out.append(self.helper.run(q, a, **kwargs))
                plane_out.append(row_out)
            out.append(plane_out)

        return out


# ============================================================
# TaskPlannerHelperV1 (max-updated + cache + 3D)
# ============================================================
class TaskPlannerHelperV1(BaseHelper):
    name = "TaskPlannerHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-planner-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"
        self.cache: Dict[int, Dict[str, Any]] = {}

    def run(self, goal: str, **kwargs) -> Dict[str, Any]:
        goal = MicroStringStripper.clean(goal)
        goal = MicroTokenLimiter.limit(goal)
        if not goal:
            return {"steps": [], "summary": ""}

        h = MicroFastHash.h(goal)
        cached = self.cache.get(h)
        if cached is not None:
            return cached

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
            env = {
                "steps": [],
                "summary": f"Planner error: {e}",
            }
            self.cache[h] = env
            return env

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

        self.cache[h] = data
        return data


class TaskPlannerHelper3D(BaseHelper):
    name = "TaskPlannerHelper3D"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-planner-v1") -> None:
        self.helper = TaskPlannerHelperV1(llm_engine, model_name)
        self.preferred_device = "gpu"

    def run_3d(
        self,
        goals_3d: List[List[List[str]]],
        **kwargs,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(goals_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = goals_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for g in row:
                    row_out.append(self.helper.run(g, **kwargs))
                plane_out.append(row_out)
            out.append(plane_out)

        return out


# ============================================================
# DomainExpertRouterHelperV1 (multi-domain, max-updated + cache + 3D)
# ============================================================
class DomainExpertRouterHelperV1(BaseHelper):
    name = "DomainExpertRouterHelper"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-domain-expert-v1") -> None:
        self.llm_engine = llm_engine
        self.model_name = model_name
        self.preferred_device = "gpu"
        self.cache: Dict[int, Dict[str, Any]] = {}

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
        query = MicroStringStripper.clean(query)
        query = MicroTokenLimiter.limit(query)
        if not query:
            return {"domain": "general", "answer": ""}

        h = MicroFastHash.h(query)
        cached = self.cache.get(h)
        if cached is not None:
            return cached

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
            env = {
                "domain": domain,
                "answer": f"Domain expert error: {e}",
            }
            self.cache[h] = env
            return env

        env = {
            "domain": domain,
            "answer": answer,
        }
        self.cache[h] = env
        return env


class DomainExpertRouterHelper3D(BaseHelper):
    name = "DomainExpertRouterHelper3D"

    def __init__(self, llm_engine, model_name: str = "syntheticmind-domain-expert-v1") -> None:
        self.helper = DomainExpertRouterHelperV1(llm_engine, model_name)
        self.preferred_device = "gpu"

    def run_3d(
        self,
        queries_3d: List[List[List[str]]],
        **kwargs,
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    row_out.append(self.helper.run(q, **kwargs))
                plane_out.append(row_out)
            out.append(plane_out)

        return out
