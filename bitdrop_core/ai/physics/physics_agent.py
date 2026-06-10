from __future__ import annotations
from .physics_engine import PhysicsEngine


class PhysicsAgent:
    """
    3D-aware PhysicsAgent wrapper.

    If the underlying PhysicsEngine supports a 3D structural view
    (e.g., PhysicsEngine v3 with _build_3d_view / _last_blocks),
    this agent can both solve problems and expose their 3D structure.
    """

    def __init__(self, engine: PhysicsEngine):
        self.engine = engine

    def solve(self, problem: str) -> str:
        """
        Standard solve — delegates directly to the engine.
        """
        return self.engine.solve(problem)

    def solve_3d(self, problem: str) -> str:
        """
        3D-aware solve:

        - builds a 3D structural view of the problem (if supported)
        - then runs the normal solver

        Behavior is identical to solve(), but ensures the engine's
        3D structures are populated for introspection.
        """
        build_3d = getattr(self.engine, "_build_3d_view", None)
        if callable(build_3d):
            build_3d(problem)
        return self.engine.solve(problem)

    def get_3d_structure(self, problem: str):
        """
        Returns the 3D structural representation of the problem
        if the engine supports it; otherwise returns None.
        """
        build_3d = getattr(self.engine, "_build_3d_view", None)
        if not callable(build_3d):
            return None
        return build_3d(problem)
