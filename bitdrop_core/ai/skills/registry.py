# syntheticmind/skills/skill_registry.py

from __future__ import annotations
from typing import Dict, Any, Optional
import traceback

from .base import Skill


class SkillRegistry:
    """
    Registry of all available skills.
    Provides:
        • safe registration
        • duplicate protection
        • structured lookup
        • metadata introspection
        • safe snapshot
        • future-proof hooks for SkillRunner + EvolutionEngine
    """

    def __init__(self):
        # skill_name -> Skill instance
        self._skills: Dict[str, Skill] = {}

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
            return {
                "ok": False,
                "error": f"Skill '{name}' is already registered",
            }

        self._skills[name] = skill

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
        return self._skills.get(name)

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

        return {
            name: {
                "description": s.description,
                "version": s.version,
            }
            for name, s in self._skills.items()
        }

    # ------------------------------------------------------------
    # SAFE SNAPSHOT (never throws)
    # ------------------------------------------------------------
    def snapshot(self) -> Dict[str, Any]:
        """
        Returns a structured snapshot of all skills.
        """

        try:
            return {
                "ok": True,
                "skills": self.list(),
                "count": len(self._skills),
                "error": None,
            }
        except Exception as e:
            return {
                "ok": False,
                "skills": {},
                "count": 0,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }
