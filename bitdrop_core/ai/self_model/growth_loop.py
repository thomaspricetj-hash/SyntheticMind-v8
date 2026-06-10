from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, List, Optional


SELF_MODEL_DIR_NAME = "self_model"
SELF_MODEL_LIVE_FILE = "self_model_live.json"
SELF_MODEL_META_FILE = "self_model_meta.json"


@dataclass
class Growth3D:
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


class SelfGrowthLoop:
    """
    SelfGrowthLoop v3 — Autonomous Behavioral Learning (Identity-Locked)

    - Uses full metadata from ConversationEngine v8
    - Learns from intent, task, routing, confidence, reasoning context
    - Integrates with reinforcement-style signals (no direct self-model rewrite)
    - Detects drift across reasoning, emotional, creative, and routing layers
    - Generates reinforcement signals for adaptive behavior
    - Produces proposed updates (but NEVER rewrites the self-model)
    - Snapshots self-model for historical tracking
    """

    def __init__(self, base_dir: str):
        self.base_dir = base_dir

        self.model_path = os.path.join(
            base_dir, "bitdrop_core", "ai", SELF_MODEL_DIR_NAME, SELF_MODEL_LIVE_FILE
        )
        self.meta_path = os.path.join(
            base_dir, "bitdrop_core", "ai", SELF_MODEL_DIR_NAME, SELF_MODEL_META_FILE
        )

        self.history_dir = os.path.join(
            base_dir, "bitdrop_core", "ai", SELF_MODEL_DIR_NAME, "self_model_history"
        )
        self.proposed_dir = os.path.join(
            base_dir, "bitdrop_core", "ai", SELF_MODEL_DIR_NAME, "proposed_updates"
        )

        os.makedirs(self.history_dir, exist_ok=True)
        os.makedirs(self.proposed_dir, exist_ok=True)

        self._last_3d: Optional[Growth3D] = None

    # ---------------------------------------------------------
    # IO HELPERS
    # ---------------------------------------------------------

    def _safe_read_json(self, path: str, default: Any) -> Any:
        if not os.path.exists(path):
            return default
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default

    def _safe_write_json(self, path: str, data: Any) -> None:
        tmp = path + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        except Exception:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

    # ---------------------------------------------------------
    # MODEL / META
    # ---------------------------------------------------------

    def load_self_model(self) -> Dict[str, Any]:
        default_model: Dict[str, Any] = {
            "version": 0,
            "personality": {
                "social_layer": "",
                "max_reply_length": 2000,
            },
            "growth_model": {
                "development_goals": {},
            },
        }
        data = self._safe_read_json(self.model_path, default_model)
        # Ensure required fields exist
        data.setdefault("personality", {}).setdefault("max_reply_length", 2000)
        data.setdefault("growth_model", {}).setdefault("development_goals", {})
        return data

    def load_meta(self) -> Dict[str, Any]:
        meta = self._safe_read_json(
            self.meta_path,
            {
                "version": 0,
                "total_interactions": 0,
                "last_snapshot_date": None,
                "last_snapshot_version": 0,
            },
        )
        meta.setdefault("version", 0)
        meta.setdefault("total_interactions", 0)
        meta.setdefault("last_snapshot_date", None)
        meta.setdefault("last_snapshot_version", 0)
        return meta

    def save_meta(self, meta: Dict[str, Any]) -> None:
        self._safe_write_json(self.meta_path, meta)

    # ---------------------------------------------------------
    # BEHAVIOR OBSERVATION
    # ---------------------------------------------------------

    def observe_behavior(self, metadata: dict, reply: str) -> Dict[str, Any]:
        reasoning = metadata.get("reasoning_context", {}) or {}
        social = metadata.get("social_read", {}) or {}

        return {
            "tone": social.get("tone"),
            "stance": social.get("stance"),
            "perspective": social.get("perspective"),
            "intent": metadata.get("intent"),
            "sub_intent": metadata.get("sub_intent"),
            "task": metadata.get("task"),
            "confidence_action": reasoning.get("confidence_action"),
            "confidence_score": reasoning.get("confidence_score"),
            "missing_info": reasoning.get("missing_info"),
            "raw_features": reasoning.get("raw_features"),
            "reply_length": len(reply or ""),
            "reply_text": reply or "",
            "model_role": metadata.get("model_role"),
            "complexity_score": metadata.get("complexity_score"),
            "memory_event": metadata.get("memory_event"),
            "nvme_event": metadata.get("nvme_event"),
            "creative_event": metadata.get("creative_event"),
        }

    # ---------------------------------------------------------
    # DRIFT DETECTION
    # ---------------------------------------------------------

    def compare_to_self_model(self, model: dict, behavior: dict) -> List[str]:
        mismatches: List[str] = []

        personality = model.get("personality", {})
        expected_social = personality.get("social_layer", "") or ""
        max_reply_length = personality.get("max_reply_length", 2000)

        tone = behavior.get("tone")
        reply_length = behavior.get("reply_length", 0)
        task = behavior.get("task")
        confidence_score = behavior.get("confidence_score") or 0.0
        model_role = behavior.get("model_role")
        reply_text = (behavior.get("reply_text") or "").lower()

        if tone in ("hurt", "frustrated") and "warm" not in expected_social:
            mismatches.append(
                "Social drift: warmth not applied when user emotional state required it."
            )

        if reply_length > max_reply_length:
            mismatches.append(
                "Reply too long: violates clarity/conciseness principle."
            )

        if task == "reasoning" and confidence_score < 0.4:
            mismatches.append(
                "Reasoning drift: low confidence during reasoning task."
            )

        if task == "coding" and model_role not in ("code", "reasoning"):
            mismatches.append(
                "Routing drift: coding task not routed to coding model."
            )

        if task == "creative" and "imagination" not in reply_text:
            mismatches.append(
                "Creative drift: insufficient imaginative expression."
            )

        if "concept" not in reply_text:
            mismatches.append(
                "Knowledge graph drift: conceptual linking missing."
            )

        return mismatches

    # ---------------------------------------------------------
    # GOAL SATISFACTION
    # ---------------------------------------------------------

    def score_goal_satisfaction(self, model: dict, behavior: dict) -> Dict[str, float]:
        scores: Dict[str, float] = {}
        goals = model.get("growth_model", {}).get("development_goals", {}) or {}

        text = (behavior.get("reply_text") or "").lower()

        if "knowledge_acquisition" in goals:
            scores["knowledge_acquisition"] = 1.0 if "concept" in text else 0.3

        if "emotional_intelligence" in goals:
            scores["emotional_intelligence"] = 1.0 if "empathy" in text else 0.5

        if "creative_expression" in goals:
            scores["creative_expression"] = 1.0 if "imagination" in text else 0.4

        if "problem_solving" in goals:
            scores["problem_solving"] = 1.0 if "solution" in text else 0.5

        if "self_awareness" in goals:
            scores["self_awareness"] = 1.0 if "introspection" in text else 0.4

        return scores

    # ---------------------------------------------------------
    # UPDATE PROPOSALS
    # ---------------------------------------------------------

    def propose_update(self, mismatches: List[str], scores: Dict[str, float]) -> Dict[str, Any]:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "mismatches": mismatches,
            "goal_scores": scores,
            "proposed_behavioral_adjustments": [
                {"action": "adjust_behavior", "reason": m}
                for m in mismatches
            ],
            "reinforce_goals": [
                {"goal": g, "score": s}
                for g, s in scores.items()
                if s < 0.6
            ],
        }

    def save_proposed_update(self, update: dict) -> None:
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(self.proposed_dir, f"proposed_update_{ts}.json")
        self._safe_write_json(path, update)

    # ---------------------------------------------------------
    # SNAPSHOTS / REINFORCEMENT
    # ---------------------------------------------------------

    def snapshot_self_model(self) -> None:
        if not os.path.exists(self.model_path):
            return

        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        snapshot_path = os.path.join(self.history_dir, f"self_model_{ts}.json")

        try:
            with open(self.model_path, "r", encoding="utf-8") as src:
                data = src.read()
            with open(snapshot_path, "w", encoding="utf-8") as dst:
                dst.write(data)
        except Exception:
            return

        meta = self.load_meta()
        meta["last_snapshot_date"] = datetime.utcnow().date().isoformat()
        meta["last_snapshot_version"] = meta.get("version", 0)
        self.save_meta(meta)

    def reinforce_growth_plan(self, scores: Dict[str, float]) -> Dict[str, str]:
        return {
            goal: ("strengthen" if score < 0.6 else "maintain")
            for goal, score in scores.items()
        }

    # ---------------------------------------------------------
    # MAIN LOOP
    # ---------------------------------------------------------

    def run(self, metadata: dict, reply: str) -> Dict[str, Any]:
        start = datetime.utcnow()

        model = self.load_self_model()
        behavior = self.observe_behavior(metadata, reply)
        mismatches = self.compare_to_self_model(model, behavior)
        scores = self.score_goal_satisfaction(model, behavior)
        reinforcement = self.reinforce_growth_plan(scores)

        meta = self.load_meta()
        meta["total_interactions"] = meta.get("total_interactions", 0) + 1
        meta["version"] = meta.get("version", 0) + 1
        self.save_meta(meta)

        if mismatches or any(s < 0.6 for s in scores.values()):
            update = self.propose_update(mismatches, scores)
            update["reinforcement"] = reinforcement
            self.save_proposed_update(update)
            self.snapshot_self_model()

        result = {
            "mismatches": mismatches,
            "scores": scores,
            "reinforcement": reinforcement,
        }

        self._last_3d = Growth3D(
            axis_x="run",
            axis_y=[
                f"intent:{metadata.get('intent')}",
                f"task:{metadata.get('task')}",
            ],
            axis_z={
                "started_at": start.isoformat(),
                "latency_ms": 0,  # caller can fill if desired
                "mismatch_count": len(mismatches),
                "goals_tracked": len(scores),
            },
        )

        return result


def run_growth_cycle(base_dir: str, metadata: Dict[str, Any], reply: str) -> Dict[str, Any]:
    loop = SelfGrowthLoop(base_dir=base_dir)
    return loop.run(metadata=metadata, reply=reply)
