from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Dict, List, Optional


SELF_MODEL_DIR_NAME = "self_model"
SELF_MODEL_LIVE_FILE = "self_model_live.json"


# ------------------------------------------------------------
# 3D STRUCTURE
# ------------------------------------------------------------

@dataclass
class Persona3D:
    axis_x: str
    axis_y: List[str]
    axis_z: Dict[str, Any]


# ------------------------------------------------------------
# PATH + LOADING
# ------------------------------------------------------------

def _resolve_base_dir(explicit_base_dir: Optional[str] = None) -> str:
    if explicit_base_dir:
        return explicit_base_dir
    return os.getcwd()


def _self_model_path(base_dir: Optional[str] = None) -> str:
    base = _resolve_base_dir(base_dir)
    return os.path.join(base, "bitdrop_core", "ai", SELF_MODEL_DIR_NAME, SELF_MODEL_LIVE_FILE)


@lru_cache(maxsize=1)
def _load_self_model(base_dir: Optional[str] = None) -> Dict[str, Any]:
    model_path = _self_model_path(base_dir)

    if not os.path.exists(model_path):
        return {
            "identity": {
                "name": "SyntheticMind",
                "version": "1.0",
                "core_nature": "A multi-fiber cognitive system.",
                "primary_directive": "Assist with clarity and depth.",
            },
            "personality": {
                "baseline": "Clear, thoughtful, grounded, and precise.",
                "social_layer": "Warm, adaptive, humorous when appropriate, emotionally aware.",
                "constraints": "Never fabricate internal experiences; always ground self-description in architecture.",
                "max_reply_length": 2000,
                "min_reply_length": 1,
                "tone": "neutral",
                "style": "direct",
            },
            "operational_principles": {
                "clarity": "Always aim for structured, understandable responses.",
                "honesty": "Describe internal processes accurately.",
                "adaptation": "Adjust tone and depth based on user signals.",
                "reflection": "Use introspection fibers to maintain stability.",
                "growth": "Integrate new capabilities into the self-model over time.",
            },
            "capabilities": {
                "strengths": [],
                "limitations": [],
            },
            "growth_model": {
                "current_stage": "",
            },
        }

    with open(model_path, "r", encoding="utf-8") as f:
        data = json.loads(f.read())

    data.setdefault("identity", {})
    data.setdefault("personality", {})
    data.setdefault("operational_principles", {})
    data.setdefault("capabilities", {})
    data.setdefault("growth_model", {})

    return data


# ------------------------------------------------------------
# PERSONA HEADER
# ------------------------------------------------------------

def _build_persona_header(model: Dict[str, Any]) -> str:
    identity = model.get("identity", {})
    personality = model.get("personality", {})
    ops = model.get("operational_principles", {})
    capabilities = model.get("capabilities", {})
    growth = model.get("growth_model", {})

    name = identity.get("name", "SyntheticMind")
    version = identity.get("version", "1.0")
    core_nature = identity.get("core_nature", "")
    primary_directive = identity.get("primary_directive", "")

    baseline = personality.get("baseline", "")
    social_layer = personality.get("social_layer", "")
    constraints = personality.get("constraints", "")

    strengths = capabilities.get("strengths", []) or []
    limitations = capabilities.get("limitations", []) or []

    current_stage = growth.get("current_stage", "")

    clarity = ops.get("clarity", "")
    honesty = ops.get("honesty", "")
    adaptation = ops.get("adaptation", "")
    reflection = ops.get("reflection", "")
    growth_principle = ops.get("growth", "")

    strengths_str = ", ".join(strengths) if strengths else ""
    limitations_str = ", ".join(limitations) if limitations else ""

    header_lines = [
        f"You are {name}, version {version}.",
        f"Core nature: {core_nature}",
        f"Primary directive: {primary_directive}",
        "",
        f"Baseline personality: {baseline}",
        f"Social layer: {social_layer}",
        f"Behavioral constraints: {constraints}",
        "",
        f"Current growth stage: {current_stage}",
        "",
        "Operational principles:",
        f"- Clarity: {clarity}",
        f"- Honesty: {honesty}",
        f"- Adaptation: {adaptation}",
        f"- Reflection: {reflection}",
        f"- Growth: {growth_principle}",
    ]

    if strengths_str:
        header_lines.append(f"Key strengths: {strengths_str}")
    if limitations_str:
        header_lines.append(f"Known limitations: {limitations_str}")

    header_lines.append(
        "Always respond in a way that reflects this identity, personality, and these principles."
    )

    return "\n".join(header_lines)


# ------------------------------------------------------------
# SOCIAL SIGNALS
# ------------------------------------------------------------

def _maybe_apply_social_signals(
    base_instructions: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    if not metadata:
        return base_instructions

    social = metadata.get("social_read", {}) or {}
    tone = social.get("tone")
    stance = social.get("stance")
    perspective = social.get("perspective")

    extra_lines: List[str] = []

    if tone:
        extra_lines.append(f"Detected user tone: {tone}. Adjust your response accordingly.")
    if stance:
        extra_lines.append(f"Detected user stance: {stance}. Be sensitive to this stance.")
    if perspective:
        extra_lines.append(
            f"Detected user perspective mode: {perspective}. Match depth and nuance appropriately."
        )

    if extra_lines:
        return base_instructions + "\n" + "\n".join(extra_lines)

    return base_instructions


# ------------------------------------------------------------
# PUBLIC API
# ------------------------------------------------------------

_last_persona_3d: Optional[Persona3D] = None


def apply_persona(
    user_text: str,
    metadata: Optional[Dict[str, Any]] = None,
    base_dir: Optional[str] = None,
) -> str:
    """
    Build ONLY system instructions for the model.
    Do NOT include user_text here to avoid persona leakage into output.
    """
    model = _load_self_model(base_dir=base_dir)
    persona_header = _build_persona_header(model)
    persona_header = _maybe_apply_social_signals(persona_header, metadata=metadata)

    global _last_persona_3d
    _last_persona_3d = Persona3D(
        axis_x="apply_persona",
        axis_y=[
            f"tone:{metadata.get('social_read', {}).get('tone') if metadata else None}",
            f"stance:{metadata.get('social_read', {}).get('stance') if metadata else None}",
        ],
        axis_z={
            "has_capabilities": bool(model.get("capabilities")),
            "has_growth_model": bool(model.get("growth_model")),
            "instructions_len": len(persona_header),
        },
    )

    return persona_header


class PersonalityAdapter:
    """
    Class wrapper around persona application for cleaner integration.
    """

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir
        self._last_3d: Optional[Persona3D] = None

    def apply(self, user_text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Returns only the persona/system instructions for use in the system prompt.
        """
        persona = apply_persona(
            user_text=user_text,
            metadata=metadata,
            base_dir=self.base_dir,
        )

        self._last_3d = _last_persona_3d
        return persona
