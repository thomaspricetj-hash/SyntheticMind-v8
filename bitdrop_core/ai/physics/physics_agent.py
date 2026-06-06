from __future__ import annotations
from .physics_engine import PhysicsEngine


class PhysicsAgent:
    def __init__(self, engine: PhysicsEngine):
        self.engine = engine

    def solve(self, problem: str) -> str:
        return self.engine.solve(problem)
