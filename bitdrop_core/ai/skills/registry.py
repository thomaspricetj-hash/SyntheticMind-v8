# syntheticmind/skills/skill_registry.py

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
import traceback

from .base import Skill


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class SkillRegistry3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# SKILL REGISTRY — MAX SPEED + 3D‑MAX
# ============================================================

class SkillRegistry:
    """
    Registry of all available skills (3D‑MAX Edition).
    Provides:
        • safe registration
        • duplicate protection
        • structured lookup
        • metadata introspection
        • safe snapshot
        • future-proof hooks for SkillRunner + EvolutionEngine
        • 3D‑MAX introspection for registry operations
    """

    def __init__(self):
        # skill_name -> Skill instance
        self._skills: Dict[str, Skill] = {}
        self._last_3d: Optional[SkillRegistry3D] = None

    # ------------------------------------------------------------
    # REGISTER SKILL
    # ------------------------------------------------------------
    def register(self, skill: Skill) -> Dict[str, Any]:
        """
        Register a skill instance.
        Returns a structured envelope.
        """

        name = skill.name

        if name in self._skills:
            self._last_3d = SkillRegistry3D(
                axis_x="register",
                axis_y=[f"skill:{name}"],
                axis_z={"ok": False, "reason": "duplicate"},
            )
            return {
                "ok": False,
                "error": f"Skill '{name}' is already registered",
            }

        self._skills[name] = skill

        self._last_3d = SkillRegistry3D(
            axis_x="register",
            axis_y=[f"skill:{name}"],
            axis_z={
                "ok": True,
                "count": len(self._skills),
                "version": skill.version,
            },
        )

        return {
            "ok": True,
            "skill": name,
            "description": skill.description,
            "version": skill.version,
        }

    # ------------------------------------------------------------
    # GET SKILL
    # ------------------------------------------------------------
    def get(self, name: str) -> Optional[Skill]:
        """
        Safe lookup. Returns None if missing.
        """
        skill = self._skills.get(name)

        self._last_3d = SkillRegistry3D(
            axis_x="get",
            axis_y=[f"skill:{name}"],
            axis_z={
                "found": skill is not None,
                "count": len(self._skills),
            },
        )

        return skill

    # ------------------------------------------------------------
    # LIST SKILLS
    # ------------------------------------------------------------
    def list(self) -> Dict[str, Dict[str, Any]]:
        """
        Returns a structured list of all registered skills:
            {
                "skill_name": {
                    "description": "...",
                    "version": "...",
                }
            }
        """

        listing = {
            name: {
                "description": s.description,
                "version": s.version,
            }
            for name, s in self._skills.items()
        }

        self._last_3d = SkillRegistry3D(
            axis_x="list",
            axis_y=[f"count:{len(listing)}"],
            axis_z={},
        )

        return listing

    # ------------------------------------------------------------
    # SAFE SNAPSHOT (never throws)
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a structured snapshot of all skills.
        """

        try:
            skills = self.list()
            snap = {
                "ok": True,
                "skills": skills,
                "count": len(self._skills),
                "error": None,
            }

            self._last_3d = SkillRegistry3D(
                axis_x="snapshot",
                axis_y=[f"count:{len(self._skills)}"],
                axis_z={"ok": True},
            )

            return snap

        except Exception as e:
            self._last_3d = SkillRegistry3D(
                axis_x="snapshot",
                axis_y=["exception"],
                axis_z={"ok": False, "error": str(e)},
            )
            return {
                "ok": False,
                "skills": {},
                "count": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

