from typing import Any, Dict, Optional
from dataclasses import dataclass

try:
    from syntheticmind.physics.engine import PhysicsEngine, PhysicsConfig
except Exception:
    PhysicsEngine = None
    PhysicsConfig = None


# ============================================================
# 3D‑MAX STRUCTURE
# ============================================================

@dataclass
class Physics3D:
    axis_x: str
    axis_y: list
    axis_z: dict


# ============================================================
# ENGINE CACHE
# ============================================================

_engine: Optional[Any] = None


def _get_engine():
    """
    Lazy-load and cache the physics engine.
    Ensures we never repeatedly reinitialize GPU/CPU resources.
    """
    global _engine
    if _engine is None and PhysicsEngine is not None:
        try:
            _engine = PhysicsEngine(PhysicsConfig(enabled=True))
        except Exception:
            _engine = None
    return _engine


# ------------------------------------------------------------
# Utility: extract float with safe fallback + error reporting
# ------------------------------------------------------------
def _get_float(args: Dict[str, Any], key: str, default: float = 0.0):
    try:
        return float(args.get(key, default))
    except Exception:
        raise ValueError(f"invalid numeric value for '{key}'")


# ============================================================
# MAIN TOOL — MAX PHYSICS + 3D‑MAX
# ============================================================

def physics_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    High‑level physics helper tool (3D‑MAX Edition).

    Supported modes:
        • kinematics_1d
        • time_to_reach
        • velocity_final
        • displacement
        • acceleration
        • energy_kinetic
        • energy_potential

    Automatically validates inputs and returns structured errors.
    """

    eng = _get_engine()
    if eng is None:
        return {
            "error": "PhysicsEngine not available",
            "_3d": Physics3D(
                axis_x="physics_tool",
                axis_y=["engine_missing"],
                axis_z={"ok": False},
            ),
        }

    mode = str(args.get("mode", "")).strip().lower()
    if not mode:
        return {
            "error": "missing mode",
            "_3d": Physics3D(
                axis_x="physics_tool",
                axis_y=["missing_mode"],
                axis_z={"ok": False},
            ),
        }

    try:
        # --------------------------------------------------------
        # 1D KINEMATICS
        # --------------------------------------------------------
        if mode == "kinematics_1d":
            x0 = _get_float(args, "x0")
            v0 = _get_float(args, "v0")
            a = _get_float(args, "a")
            t = _get_float(args, "t")
            out = eng.kinematics_1d(x0, v0, a, t)
            return {
                **out,
                "_3d": Physics3D(
                    axis_x="physics_tool",
                    axis_y=["kinematics_1d"],
                    axis_z={"ok": True},
                ),
            }

        # --------------------------------------------------------
        # TIME TO REACH POSITION
        # --------------------------------------------------------
        if mode == "time_to_reach":
            x0 = _get_float(args, "x0")
            v0 = _get_float(args, "v0")
            a = _get_float(args, "a")
            x_target = _get_float(args, "x_target")
            out = eng.time_to_reach(x0, v0, a, x_target)
            return {
                **out,
                "_3d": Physics3D(
                    axis_x="physics_tool",
                    axis_y=["time_to_reach"],
                    axis_z={"ok": True},
                ),
            }

        # --------------------------------------------------------
        # FINAL VELOCITY
        # --------------------------------------------------------
        if mode == "velocity_final":
            v0 = _get_float(args, "v0")
            a = _get_float(args, "a")
            t = _get_float(args, "t")
            out = {"v_final": v0 + a * t}
            return {
                **out,
                "_3d": Physics3D(
                    axis_x="physics_tool",
                    axis_y=["velocity_final"],
                    axis_z={"ok": True},
                ),
            }

        # --------------------------------------------------------
        # DISPLACEMENT
        # --------------------------------------------------------
        if mode == "displacement":
            x0 = _get_float(args, "x0")
            v0 = _get_float(args, "v0")
            t = _get_float(args, "t")
            a = _get_float(args, "a")
            out = {"x": x0 + v0 * t + 0.5 * a * t * t}
            return {
                **out,
                "_3d": Physics3D(
                    axis_x="physics_tool",
                    axis_y=["displacement"],
                    axis_z={"ok": True},
                ),
            }

        # --------------------------------------------------------
        # ACCELERATION
        # --------------------------------------------------------
        if mode == "acceleration":
            v = _get_float(args, "v")
            v0 = _get_float(args, "v0")
            t = _get_float(args, "t")
            if t == 0:
                return {
                    "error": "time cannot be zero",
                    "_3d": Physics3D(
                        axis_x="physics_tool",
                        axis_y=["acceleration"],
                        axis_z={"ok": False},
                    ),
                }
            out = {"a": (v - v0) / t}
            return {
                **out,
                "_3d": Physics3D(
                    axis_x="physics_tool",
                    axis_y=["acceleration"],
                    axis_z={"ok": True},
                ),
            }

        # --------------------------------------------------------
        # KINETIC ENERGY
        # --------------------------------------------------------
        if mode == "energy_kinetic":
            m = _get_float(args, "m")
            v = _get_float(args, "v")
            out = {"ke": 0.5 * m * v * v}
            return {
                **out,
                "_3d": Physics3D(
                    axis_x="physics_tool",
                    axis_y=["energy_kinetic"],
                    axis_z={"ok": True},
                ),
            }

        # --------------------------------------------------------
        # POTENTIAL ENERGY
        # --------------------------------------------------------
        if mode == "energy_potential":
            m = _get_float(args, "m")
            h = _get_float(args, "h")
            g = _get_float(args, "g", 9.81)
            out = {"pe": m * g * h}
            return {
                **out,
                "_3d": Physics3D(
                    axis_x="physics_tool",
                    axis_y=["energy_potential"],
                    axis_z={"ok": True},
                ),
            }

        # --------------------------------------------------------
        # UNKNOWN MODE
        # --------------------------------------------------------
        return {
            "error": f"unknown mode '{mode}'",
            "_3d": Physics3D(
                axis_x="physics_tool",
                axis_y=["unknown_mode"],
                axis_z={"mode": mode},
            ),
        }

    except ValueError as ve:
        return {
            "error": str(ve),
            "_3d": Physics3D(
                axis_x="physics_tool",
                axis_y=["value_error"],
                axis_z={"error": str(ve)},
            ),
        }

    except Exception as e:
        return {
            "error": f"physics_tool failed: {e}",
            "_3d": Physics3D(
                axis_x="physics_tool",
                axis_y=["exception"],
                axis_z={"error": str(e)},
            ),
        }


