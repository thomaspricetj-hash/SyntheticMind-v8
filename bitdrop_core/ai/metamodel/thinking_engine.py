from __future__ import annotations

import hashlib
import time
import re
from typing import Any, Dict, List, Optional, Tuple, Callable


class ThoughtCache:
    """
    Simple bounded cache for thinking results.
    Keyed by (intent, prompt_hash).
    """

    def __init__(self, max_size: int = 512) -> None:
        self.max_size = max_size
        self._store: Dict[str, Dict[str, Any]] = {}
        self._order: List[str] = []

    def _make_key(self, intent: str, prompt: str, metadata: Optional[Dict[str, Any]]) -> str:
        h = hashlib.sha256()
        h.update(intent.encode("utf-8"))
        h.update(prompt.encode("utf-8"))
        if metadata:
            h.update(repr(sorted(metadata.items())).encode("utf-8"))
        return h.hexdigest()

    def get(
        self,
        intent: str,
        prompt: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        key = self._make_key(intent, prompt, metadata)
        if key not in self._store:
            return None
        if key in self._order:
            self._order.remove(key)
        self._order.append(key)
        return self._store[key]

    def set(
        self,
        intent: str,
        prompt: str,
        metadata: Optional[Dict[str, Any]],
        value: Dict[str, Any],
    ) -> None:
        key = self._make_key(intent, prompt, metadata)
        if key in self._store:
            self._store[key] = value
            if key in self._order:
                self._order.remove(key)
            self._order.append(key)
            return

        if len(self._order) >= self.max_size:
            oldest = self._order.pop(0)
            self._store.pop(oldest, None)

        self._store[key] = value
        self._order.append(key)


class MicroHelperRegistry:
    """
    Micro‑helper registry for domain‑specific reasoning.

    Each helper is a callable:
        (runtime, subproblem, intent, metadata) -> envelope: Dict[str, Any]

    Envelope shape (recommended, but tolerant):
        {
            "text": str,              # main answer text
            "sections": [...],        # optional structured sections
            "domain": str,            # e.g. "physics", "math", ...
            "valid": bool,            # helper's own validity flag
            ...                       # any extra metadata
        }
    """

    # MAX‑3D aligned physics keywords (mirrors Router deep‑physics override)
    PHYSICS_KEYWORDS = [
        "photon rocket", "relativistic rocket", "lorentz", "gamma",
        "c^2", "rest mass energy", "energy–momentum", "energy-momentum",
        "schwarzschild", "kerr", "ergosphere", "event horizon",
        "geodesic", "null geodesic", "timelike", "spacelike",
        "general relativity", "special relativity",
        "force", "mass", "velocity", "quantum", "entangled",
    ]

    def __init__(self) -> None:
        self._helpers: Dict[str, Callable[..., Dict[str, Any]]] = {}

    def register(self, name: str, fn: Callable[..., Dict[str, Any]]) -> None:
        self._helpers[name] = fn

    def get(self, name: str) -> Optional[Callable[..., Dict[str, Any]]]:
        return self._helpers.get(name)

    def detect_domains(self, text: str) -> List[str]:
        """
        MAX‑3D domain detector:
          • Physics: GR/SR/relativistic/quantum + classical terms
          • Math: presence of math symbols / digits
          • Logic: implication / proof language
          • Code: code keywords
          • Fallback: generic
        """
        t = text.lower()
        domains: List[str] = []

        # Physics (MAX‑3D aligned with Router)
        if any(w in t for w in self.PHYSICS_KEYWORDS):
            domains.append("physics")

        # Math
        if re.search(r"[0-9\+\-\*/\^=\(\)]", text):
            domains.append("math")

        # Logic
        if any(w in t for w in ["if and only if", "iff", "therefore", "implies", "assume", "suppose"]):
            domains.append("logic")

        # Code
        if any(w in t for w in ["def ", "class ", "import ", "return ", "for ", "while ", "try:", "except "]):
            domains.append("code")

        if not domains:
            domains.append("generic")

        return domains


class ThinkingEngine:
    """
    ThinkingEngine — hybrid of:
        A) Symbolic‑chain thinker
        B) Multi‑pass deliberation
        C) 3D tensor thinker (passes × subproblems × candidates)
        D) MAX‑3D helper integration (physics/math/logic/code + ReasoningHelperV2)

    Public APIs:
        think()       — single prompt
        think_batch() — 2D batch
        think_3d()    — full 3D‑MAX tensor
    """

    def __init__(
        self,
        runtime: Any,
        *,
        physics_helper: Any = None,
        math_helper: Any = None,
        logic_helper: Any = None,
        code_helper: Any = None,
        reasoning_helper: Any = None,
    ) -> None:
        """
        runtime: object providing at least runtime.local_reasoner.generate(...)
        helpers (optional):
            - physics_helper: PhysicsHelper or PhysicsHelper3D
            - math_helper:    MathHelper or MathHelper3D
            - logic_helper:   LogicHelper or LogicHelper3D
            - code_helper:    CodeHelper
            - reasoning_helper: ReasoningHelperV2
        If not provided, we try to pull them from runtime.* attributes.
        """
        self.runtime = runtime
        self.cache = ThoughtCache(max_size=512)
        self.micro_helpers = MicroHelperRegistry()

        # Attach helpers (explicit overrides > runtime attributes)
        self.physics_helper = physics_helper or getattr(runtime, "physics_helper", None)
        self.math_helper = math_helper or getattr(runtime, "math_helper", None)
        self.logic_helper = logic_helper or getattr(runtime, "logic_helper", None)
        self.code_helper = code_helper or getattr(runtime, "code_helper", None)
        self.reasoning_helper = reasoning_helper or getattr(runtime, "reasoning_helper", None)

        self._register_default_helpers()

    # ------------------------------------------------------------------
    # Micro‑helpers (now wired to MAX‑3D helpers when available)
    # ------------------------------------------------------------------
    def _wrap_helper_envelope(self, text: str, domain: str) -> Dict[str, Any]:
        return {
            "text": text.strip(),
            "sections": [],
            "domain": domain,
            "valid": bool(text.strip()),
        }

    def _call_structured_helper(
        self,
        helper: Any,
        subproblem: str,
        domain: str,
        intent: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Call a structured helper (Physics/Math/Logic/Code) in a tolerant way:
        - If it exposes .process(query, lang_info, memory_info), use that.
        - If it exposes .process_3d, call with a 1×1×1 tensor.
        - If it returns a dict with "text", pass it through.
        - If it returns a string, wrap it.
        """
        lang_info = metadata.get("lang_info") or {}
        memory_info = metadata.get("memory_info") or {}

        try:
            if hasattr(helper, "process"):
                env = helper.process(subproblem, lang_info, memory_info)
            elif hasattr(helper, "process_3d"):
                env_3d = helper.process_3d([[[subproblem]]], lang_info, memory_info)
                env = env_3d[0][0][0]
            else:
                # Fallback: treat helper as callable returning string
                text = str(helper(subproblem))
                return self._wrap_helper_envelope(text, domain)

            if isinstance(env, dict) and "text" in env:
                # Ensure domain + validity are present
                env.setdefault("domain", domain)
                env.setdefault("valid", True)
                return env

            # Fallback: wrap whatever came back
            return self._wrap_helper_envelope(str(env), domain)

        except Exception:
            return self._wrap_helper_envelope("", domain)

    def _register_default_helpers(self) -> None:
        # Physics helper
        def physics_helper(runtime: Any, subproblem: str, intent: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            if self.physics_helper is not None:
                return self._call_structured_helper(self.physics_helper, subproblem, "physics", intent, metadata)

            prompt = (
                "You are a theoretical physics reasoning module. "
                "Use correct relativistic and quantum principles. "
                "No analogies, no fluff. Answer precisely.\n\n"
                f"Problem: {subproblem}"
            )
            out = runtime.local_reasoner.generate(
                prompt=prompt,
                meta={**metadata, "mode": "physics_helper", "intent": intent},
            )
            text = out.get("text", "") if isinstance(out, dict) else str(out)
            return self._wrap_helper_envelope(text, "physics")

        # Math helper
        def math_helper(runtime: Any, subproblem: str, intent: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            if self.math_helper is not None:
                return self._call_structured_helper(self.math_helper, subproblem, "math", intent, metadata)

            prompt = (
                "You are a mathematical reasoning module. "
                "Derive equations and conditions explicitly. "
                "Think step-by-step internally but output only the final reasoning.\n\n"
                f"Problem: {subproblem}"
            )
            out = runtime.local_reasoner.generate(
                prompt=prompt,
                meta={**metadata, "mode": "math_helper", "intent": intent},
            )
            text = out.get("text", "") if isinstance(out, dict) else str(out)
            return self._wrap_helper_envelope(text, "math")

        # Logic helper
        def logic_helper(runtime: Any, subproblem: str, intent: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            if self.logic_helper is not None:
                return self._call_structured_helper(self.logic_helper, subproblem, "logic", intent, metadata)

            prompt = (
                "You are a formal logic reasoning module. "
                "Focus on consistency, implications, and contradictions.\n\n"
                f"Problem: {subproblem}"
            )
            out = runtime.local_reasoner.generate(
                prompt=prompt,
                meta={**metadata, "mode": "logic_helper", "intent": intent},
            )
            text = out.get("text", "") if isinstance(out, dict) else str(out)
            return self._wrap_helper_envelope(text, "logic")

        # Code helper
        def code_helper(runtime: Any, subproblem: str, intent: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            if self.code_helper is not None:
                # CodeHelper already returns a structured envelope
                try:
                    env = self.code_helper.process(
                        subproblem,
                        metadata.get("lang_info") or {},
                        metadata.get("memory_info") or {},
                    )
                    if isinstance(env, dict):
                        env.setdefault("domain", "code")
                        env.setdefault("valid", env.get("valid", env.get("detected", True)))
                        return env
                    return self._wrap_helper_envelope(str(env), "code")
                except Exception:
                    return self._wrap_helper_envelope("", "code")

            prompt = (
                "You are a code reasoning module. "
                "Explain behavior, edge cases, and correctness.\n\n"
                f"Problem: {subproblem}"
            )
            out = runtime.local_reasoner.generate(
                prompt=prompt,
                meta={**metadata, "mode": "code_helper", "intent": intent},
            )
            text = out.get("text", "") if isinstance(out, dict) else str(out)
            return self._wrap_helper_envelope(text, "code")

        # Generic helper
        def generic_helper(runtime: Any, subproblem: str, intent: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
            prompt = (
                "You are a deep reasoning module. "
                "Be concise, precise, and non‑fluffy.\n\n"
                f"Problem: {subproblem}"
            )
            out = runtime.local_reasoner.generate(
                prompt=prompt,
                meta={**metadata, "mode": "generic_helper", "intent": intent},
            )
            text = out.get("text", "") if isinstance(out, dict) else str(out)
            return self._wrap_helper_envelope(text, "generic")

        self.micro_helpers.register("physics", physics_helper)
        self.micro_helpers.register("math", math_helper)
        self.micro_helpers.register("logic", logic_helper)
        self.micro_helpers.register("code", code_helper)
        self.micro_helpers.register("generic", generic_helper)

    # ------------------------------------------------------------------
    # Core thinking pipeline
    # ------------------------------------------------------------------
    def _decompose(self, prompt: str) -> List[str]:
        parts = [p.strip() for p in re.split(r"\?+", prompt) if p.strip()]
        if not parts:
            return [prompt.strip()]
        return parts

    def _baseline_reason(
        self,
        subproblem: str,
        intent: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        prompt = (
            "You are performing baseline deep reasoning. "
            "Answer precisely and concisely.\n\n"
            f"Problem: {subproblem}"
        )
        out = self.runtime.local_reasoner.generate(
            prompt=prompt,
            meta={**metadata, "mode": "baseline", "intent": intent},
        )
        text = out.get("text", "") if isinstance(out, dict) else str(out)
        return {
            "text": text.strip(),
            "sections": [],
            "domain": "baseline",
            "valid": bool(text.strip()),
        }

    def _run_micro_helpers(
        self,
        subproblem: str,
        intent: str,
        metadata: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        domains = self.micro_helpers.detect_domains(subproblem)
        candidates: List[Dict[str, Any]] = []
        for d in domains:
            helper = self.micro_helpers.get(d)
            if not helper:
                continue
            try:
                env = helper(self.runtime, subproblem, intent, metadata)
                if isinstance(env, dict) and env.get("text", "").strip():
                    env.setdefault("domain", d)
                    candidates.append(env)
            except Exception:
                continue
        return candidates

    def _consistency_merge(
        self,
        baseline: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Multi‑pass deliberation with helper priority:
        - prefer physics/math/logic/code when present and valid
        - fall back to baseline
        - avoid obvious contradictions by simple heuristics
        """
        if not candidates:
            return baseline

        priority = {"physics": 5, "math": 4, "logic": 3, "code": 2, "generic": 1, "baseline": 0}

        def score(env: Dict[str, Any]) -> int:
            d = env.get("domain", "generic")
            base = priority.get(d, 0)
            if not env.get("valid", True):
                base -= 2
            return base

        candidates_sorted = sorted(candidates, key=score, reverse=True)
        best = candidates_sorted[0]
        best_text = best.get("text", "").strip()
        base_text = baseline.get("text", "").strip()

        if base_text and best_text and base_text not in best_text and best_text not in base_text:
            merged_text = f"{best_text}\n\n(Consistent with baseline reasoning: {base_text})"
        else:
            merged_text = best_text or base_text

        merged = dict(best)
        merged["text"] = merged_text
        merged.setdefault("domain", best.get("domain", "merged"))
        merged.setdefault("valid", True)
        return merged

    def _build_reasoning_context(
        self,
        subproblems: List[str],
        merged_envs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Build a compact context object from merged helper envelopes
        to feed into ReasoningHelperV2 as memory_info.
        """
        ctx: Dict[str, Any] = {
            "subproblems": subproblems,
            "domains": [],
            "by_domain": {},
        }

        for env in merged_envs:
            d = env.get("domain", "unknown")
            ctx["domains"].append(d)
            ctx["by_domain"].setdefault(d, [])
            ctx["by_domain"][d].append({
                "text": env.get("text", ""),
                "sections": env.get("sections", []),
                "valid": env.get("valid", True),
            })

        return ctx

    def _think_single_internal(
        self,
        prompt: str,
        intent: str,
        metadata: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Internal 3D tensor thinking:
            tensor[pass][subproblem][candidate]
        Pass 0: baseline
        Pass 1: micro‑helpers (MAX‑3D helpers when available)
        Pass 2: consistency merge
        Pass 3: optional ReasoningHelperV2 refinement
        """
        meta = metadata or {}
        start = time.time()

        subproblems = self._decompose(prompt)
        tensor: List[List[List[Dict[str, Any]]]] = []  # [pass][subproblem][candidate]

        # Pass 0 — baseline
        pass0: List[List[Dict[str, Any]]] = []
        for sp in subproblems:
            baseline_env = self._baseline_reason(sp, intent, meta)
            pass0.append([{"type": "baseline", "env": baseline_env}])
        tensor.append(pass0)

        # Pass 1 — micro‑helpers
        pass1: List[List[Dict[str, Any]]] = []
        for idx, sp in enumerate(subproblems):
            candidates_env = self._run_micro_helpers(sp, intent, meta)
            cand_list: List[Dict[str, Any]] = []
            if not candidates_env:
                candidates_env = [tensor[0][idx][0]["env"]]
            for env in candidates_env:
                cand_list.append({"type": "micro", "env": env})
            pass1.append(cand_list)
        tensor.append(pass1)

        # Pass 2 — consistency merge
        final_parts: List[str] = []
        merged_envs: List[Dict[str, Any]] = []
        pass2: List[List[Dict[str, Any]]] = []
        for i, sp in enumerate(subproblems):
            baseline_env = tensor[0][i][0]["env"]
            micro_envs = [c["env"] for c in tensor[1][i]]
            merged_env = self._consistency_merge(baseline_env, micro_envs)
            merged_envs.append(merged_env)
            final_parts.append(merged_env.get("text", "").strip())
            pass2.append([{"type": "merged", "env": merged_env}])
        tensor.append(pass2)

        # Pass 3 — ReasoningHelperV2 refinement (if available)
        final_answer = "\n\n".join(p for p in final_parts if p)
        reasoning_refined = None
        if self.reasoning_helper is not None:
            try:
                ctx = self._build_reasoning_context(subproblems, merged_envs)
                lang_info = meta.get("lang_info") or {}
                memory_info = {
                    "helper_context": ctx,
                    "metadata": meta,
                }
                rh_out = self.reasoning_helper.run(
                    prompt,
                    lang_info=lang_info,
                    memory_info=memory_info,
                )
                if isinstance(rh_out, dict) and rh_out.get("ok"):
                    reasoning_refined = rh_out
                    if rh_out.get("answer"):
                        final_answer = rh_out["answer"]
            except Exception:
                reasoning_refined = None

        latency_ms = int((time.time() - start) * 1000)

        return {
            "final": final_answer,
            "tensor": tensor,
            "tensor_shape": (
                len(tensor),
                len(subproblems),
                max(len(row) for row in tensor[1]) if tensor[1] else 1,
            ),
            "subproblems": subproblems,
            "intent": intent,
            "latency_ms": latency_ms,
            "reasoning_helper": reasoning_refined,
        }

    # ------------------------------------------------------------------
    # Public APIs
    # ------------------------------------------------------------------
    def think(
        self,
        prompt: str,
        intent: str = "deep_thinking",
        metadata: Optional[Dict[str, Any]] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Single‑prompt thinking entrypoint.
        Returns:
            {
                "final": str,
                "tensor": [...],
                "tensor_shape": (passes, subproblems, max_candidates),
                "subproblems": [...],
                "intent": str,
                "latency_ms": int,
                "cache_hit": bool,
                "reasoning_helper": Optional[dict],
            }
        """
        cached = self.cache.get(intent, prompt, metadata) if use_cache else None
        if cached is not None:
            out = dict(cached)
            out["cache_hit"] = True
            return out

        result = self._think_single_internal(prompt, intent, metadata)
        result["cache_hit"] = False

        if use_cache:
            self.cache.set(intent, prompt, metadata, result)

        return result

    def think_batch(
        self,
        requests: List[Dict[str, Any]],
        use_cache: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        2D batch thinking.
        Each request:
            {
                "prompt": str,
                "intent": str (optional),
                "metadata": dict (optional),
            }
        """
        out: List[Dict[str, Any]] = []
        for req in requests:
            prompt = req.get("prompt", "") or ""
            intent = req.get("intent", "deep_thinking")
            metadata = req.get("metadata")
            out.append(self.think(prompt, intent=intent, metadata=metadata, use_cache=use_cache))
        return out

    def think_3d(
        self,
        requests_3d: List[List[List[Dict[str, Any]]]],
        use_cache: bool = True,
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        3D‑MAX tensor thinking.
        Shape:
            requests_3d[d][h][w] -> same shape of result dicts.

        Each cell request:
            {
                "prompt": str,
                "intent": str (optional),
                "metadata": dict (optional),
            }
        """
        depth = len(requests_3d)
        if depth == 0:
            return []

        out_tensor: List[List[List[Dict[str, Any]]]] = []
        for plane in requests_3d:
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for req in row:
                    prompt = req.get("prompt", "") or ""
                    intent = req.get("intent", "deep_thinking")
                    metadata = req.get("metadata")
                    row_out.append(self.think(prompt, intent=intent, metadata=metadata, use_cache=use_cache))
                plane_out.append(row_out)
            out_tensor.append(plane_out)

        return out_tensor


