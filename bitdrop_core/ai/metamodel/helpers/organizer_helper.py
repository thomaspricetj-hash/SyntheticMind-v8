import time
import subprocess
import math
import os

class OrganizerHelperV6:
    """
    OrganizerHelperV6 (MAX)
    • Dynamic CPU/GPU routing
    • GPU util + VRAM + temperature sensing
    • Helper timing history (EMA)
    • Priority-based device assignment
    • Auto-fallback when GPU is overloaded
    • Self-optimizing per request
    • CPU load spreading across all cores
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
        self.helper_timings = {}
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
    # Main organizer
    # ------------------------------------------------------------
    def organize(self, helpers: dict):
        util, mem_ratio, temp = self._get_gpu_state()
        self._update_mode(util, mem_ratio, temp)

        for key, h in helpers.items():
            name = getattr(h, "name", None)
            if not name:
                continue

            device = self._assign_device(name, util, mem_ratio, temp)
            h.preferred_device = device

            # ⭐ CPU load spreading
            if device == "cpu":
                h.cpu_slot = self._assign_cpu_slot()
                if self.logger:
                    self.logger.debug(f"[Organizer] {name} → CPU (core {h.cpu_slot})")
            else:
                h.cpu_slot = None
                if self.logger:
                    self.logger.debug(f"[Organizer] {name} → GPU")

        return helpers


