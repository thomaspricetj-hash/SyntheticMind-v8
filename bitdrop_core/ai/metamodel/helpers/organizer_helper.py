import time
import subprocess
import math
import os
from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class Helper3D:
    name: str
    axis_x: str          # device: "cpu" / "gpu"
    axis_y: Dict[str, Any]  # timing, mode, cpu_slot
    axis_z: Dict[str, Any]  # gpu state snapshot


class OrganizerHelperV6:
    """
    OrganizerHelperV6 (MAX, 3D-aware)
    • Dynamic CPU/GPU routing
    • GPU util + VRAM + temperature sensing
    • Helper timing history (EMA)
    • Priority-based device assignment
    • Auto-fallback when GPU is overloaded
    • Self-optimizing per request
    • CPU load spreading across all cores
    • 3D helper layout (device / timing / gpu-state)
    """

    PRIORITY_GPU = {
        "EmbeddingHelper",
        "MathHelper",
        "PhysicsHelper",
        "CompressionHelper",
        "DeepPatternHelper",
        "TensorHelper",
    }

    PRIORITY_CPU = {
        "ReasonTalkHelper",
        "SummarizerHelper",
        "InstructionHelper",
        "CodeHelper",
        "SafetyHelper",
        "MemoryHelper",
        "RouterHelper",
        "MetadataHelper",
        "KVStoreHelper",
        "PlanningHelper",
        "FormatHelper",
    }

    def __init__(self, logger=None):
        self.logger = logger
        self.helper_timings: Dict[str, float] = {}
        self.mode = "balanced"

        # CPU load balancing
        self.cpu_core_count = os.cpu_count() or 8
        self.cpu_round_robin = 0

    # ------------------------------------------------------------
    # GPU state detection
    # ------------------------------------------------------------
    def _get_gpu_state(self):
        try:
            out = subprocess.check_output(
                [
                    "nvidia-smi",
                    "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
                    "--format=csv,noheader,nounits",
                ],
                encoding="utf-8"
            )
            util, mem_used, mem_total, temp = map(int, out.strip().split(","))
            mem_ratio = mem_used / mem_total
            return util, mem_ratio, temp
        except Exception:
            return 0, 0.0, 40

    # ------------------------------------------------------------
    # Timing feedback (EMA)
    # ------------------------------------------------------------
    def record_timing(self, helper_name: str, duration: float):
        prev = self.helper_timings.get(helper_name, duration)
        ema = (prev * 0.7) + (duration * 0.3)
        self.helper_timings[helper_name] = ema

    # ------------------------------------------------------------
    # Mode switching
    # ------------------------------------------------------------
    def _update_mode(self, util, mem_ratio, temp):
        if temp > 82 or mem_ratio > 0.90:
            self.mode = "safe"
        elif util < 50 and mem_ratio < 0.70:
            self.mode = "performance"
        else:
            self.mode = "balanced"

        if self.logger:
            self.logger.debug(f"[Organizer] Mode → {self.mode}")

    # ------------------------------------------------------------
    # CPU load spreading
    # ------------------------------------------------------------
    def _assign_cpu_slot(self):
        slot = self.cpu_round_robin % self.cpu_core_count
        self.cpu_round_robin += 1
        return slot

    # ------------------------------------------------------------
    # Device assignment logic
    # ------------------------------------------------------------
    def _assign_device(self, name, util, mem_ratio, temp):
        if name in self.PRIORITY_GPU:
            if self.mode == "safe":
                return "cpu"
            return "gpu"

        if name in self.PRIORITY_CPU:
            return "cpu"

        avg_time = self.helper_timings.get(name, 0)

        if avg_time > 0.060:
            if self.mode != "safe":
                return "gpu"

        if util > 85 or mem_ratio > 0.88 or temp > 80:
            return "cpu"

        return "cpu"

    # ------------------------------------------------------------
    # 3D helper layout builder
    # ------------------------------------------------------------
    def _build_helper_3d(self, name: str, device: str, cpu_slot: int, util: int, mem_ratio: float, temp: int) -> Helper3D:
        axis_x = device
        axis_y = {
            "mode": self.mode,
            "avg_time": self.helper_timings.get(name, 0.0),
            "cpu_slot": cpu_slot,
        }
        axis_z = {
            "gpu_util": util,
            "gpu_mem_ratio": mem_ratio,
            "gpu_temp": temp,
        }
        return Helper3D(name=name, axis_x=axis_x, axis_y=axis_y, axis_z=axis_z)

    # ------------------------------------------------------------
    # Main organizer
    # ------------------------------------------------------------
    def organize(self, helpers: dict):
        util, mem_ratio, temp = self._get_gpu_state()
        self._update_mode(util, mem_ratio, temp)

        # Optional: 3D map of helpers for downstream introspection
        helper_3d_map: Dict[str, Helper3D] = {}

        for key, h in helpers.items():
            name = getattr(h, "name", None)
            if not name:
                continue

            device = self._assign_device(name, util, mem_ratio, temp)
            h.preferred_device = device

            if device == "cpu":
                cpu_slot = self._assign_cpu_slot()
                h.cpu_slot = cpu_slot
                if self.logger:
                    self.logger.debug(f"[Organizer] {name} → CPU (core {cpu_slot})")
            else:
                cpu_slot = None
                h.cpu_slot = None
                if self.logger:
                    self.logger.debug(f"[Organizer] {name} → GPU")

            helper_3d_map[name] = self._build_helper_3d(
                name=name,
                device=device,
                cpu_slot=cpu_slot if cpu_slot is not None else -1,
                util=util,
                mem_ratio=mem_ratio,
                temp=temp,
            )

        # Expose 3D layout on the organizer for anyone who wants it
        self.helper_3d_map = helper_3d_map

        return helpers



