from __future__ import annotations
from typing import Any, Dict, List
import zlib


# ------------------------------------------------------------
# MICRO HELPERS
# ------------------------------------------------------------
class MicroStringStripper:
    __slots__ = ()
    @staticmethod
    def clean(text: str) -> str:
        return " ".join(text.split())


class MicroTokenLimiter:
    __slots__ = ()
    @staticmethod
    def limit(text: str, max_chars: int = 6000) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars]


class MicroFastHash:
    __slots__ = ()
    @staticmethod
    def h(text: str) -> int:
        return zlib.crc32(text.encode("utf-8"))


class MicroEntityExtractor:
    __slots__ = ()
    @staticmethod
    def extract(query: str) -> List[str]:
        tokens = query.strip().split()
        entities: List[str] = []
        current: List[str] = []

        for tok in tokens:
            if tok[:1].isupper():
                current.append(tok)
            else:
                if current:
                    entities.append(" ".join(current))
                    current = []
        if current:
            entities.append(" ".join(current))

        seen = set()
        uniq = []
        for e in entities:
            if e not in seen:
                uniq.append(e)
                seen.add(e)
        return uniq


class MicroPhysicsClassifier:
    __slots__ = ()
    @staticmethod
    def detect(q: str, clusters: Dict[str, List[str]]) -> bool:
        return any(kw in q for kws in clusters.values() for kw in kws)

    @staticmethod
    def domain(q: str, clusters: Dict[str, List[str]]) -> str:
        if any(kw in q for kw in clusters["qm"]):
            return "quantum_mechanics"
        if any(kw in q for kw in clusters["rel"]):
            return "relativity"
        if any(kw in q for kw in clusters["classical"]):
            return "classical_mechanics"
        if any(kw in q for kw in clusters["thermo"]):
            return "thermodynamics"
        if any(kw in q for kw in clusters["em"]):
            return "electromagnetism"
        return "unknown"


# ------------------------------------------------------------
# MAIN HELPER
# ------------------------------------------------------------
class PhysicsHelper:
    """
    Ultra-fast PhysicsHelper with integrated micro-helpers.
    """

    QM_KEYWORDS = [
        "quantum", "entangle", "superposition", "spin", "wavefunction",
        "bell", "epr", "hilbert", "operator", "observable", "collapse",
        "nonlocal", "eigenstate", "eigenvalue", "measurement"
    ]

    REL_KEYWORDS = [
        "relativity", "einstein", "lorentz", "time dilation", "length contraction",
        "spacetime", "gravity", "gravitational", "curvature", "geodesic"
    ]

    CLASSICAL_KEYWORDS = [
        "force", "mass", "acceleration", "velocity", "momentum", "energy",
        "work", "power", "newton", "friction", "projectile"
    ]

    THERMO_KEYWORDS = [
        "entropy", "temperature", "heat", "thermodynamics", "enthalpy",
        "free energy", "partition function"
    ]

    EM_KEYWORDS = [
        "electromagnetic", "electric", "magnetic", "field", "maxwell",
        "charge", "current", "flux", "induction"
    ]

    def __init__(self) -> None:
        self.cache: Dict[int, Dict[str, Any]] = {}
        self._clusters = {
            "qm": self.QM_KEYWORDS,
            "rel": self.REL_KEYWORDS,
            "classical": self.CLASSICAL_KEYWORDS,
            "thermo": self.THERMO_KEYWORDS,
            "em": self.EM_KEYWORDS,
        }

    # ------------------------------------------------------------
    # INTERNAL: detect physics intent
    # ------------------------------------------------------------
    def _detect_physics(self, query: str) -> bool:
        q = query.lower()
        return MicroPhysicsClassifier.detect(q, self._clusters)

    # ------------------------------------------------------------
    # INTERNAL: classify physics domain
    # ------------------------------------------------------------
    def _classify_domain(self, query: str) -> str:
        q = query.lower()
        return MicroPhysicsClassifier.domain(q, self._clusters)

    # ------------------------------------------------------------
    # INTERNAL: extract physics entities
    # ------------------------------------------------------------
    def _extract_entities(self, query: str) -> List[str]:
        return MicroEntityExtractor.extract(query)

    # ------------------------------------------------------------
    # PUBLIC: main entrypoint
    # ------------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            query = (query or "").strip()
            if not query:
                return {"detected": False}

            # Micro: normalize + limit
            query = MicroStringStripper.clean(query)
            query = MicroTokenLimiter.limit(query)

            # Micro: fast dedupe
            h = MicroFastHash.h(query)
            if h in self.cache:
                return self.cache[h]

            detected = self._detect_physics(query)
            if not detected:
                return {"detected": False}

            domain = self._classify_domain(query)
            entities = self._extract_entities(query)

            notes: List[str] = []

            if domain == "quantum_mechanics":
                notes.append("QM: consider superposition, entanglement, operators, measurement theory.")
                notes.append("QM: check if Bell-type correlations or nonlocality are implied.")

            elif domain == "relativity":
                notes.append("Relativity: consider Lorentz invariance, spacetime geometry, and invariants.")
                notes.append("Relativity: check if GR or SR applies based on context.")

            elif domain == "classical_mechanics":
                notes.append("Classical: consider Newton's laws, conservation of momentum/energy.")
                notes.append("Classical: identify forces, mass, acceleration relationships.")

            elif domain == "thermodynamics":
                notes.append("Thermo: consider entropy, free energy, and statistical ensembles.")
                notes.append("Thermo: check equilibrium vs non-equilibrium assumptions.")

            elif domain == "electromagnetism":
                notes.append("EM: consider Maxwell equations and field interactions.")
                notes.append("EM: check charge, current, flux, and induction relationships.")

            else:
                notes.append("Physics detected but domain unclear — fallback to general reasoning.")

            envelope = {
                "detected": True,
                "domain": domain,
                "entities": entities,
                "raw_query": query,
                "notes": notes,
            }

            self.cache[h] = envelope
            return envelope

        except Exception as e:
            return {
                "detected": True,
                "domain": "error",
                "entities": [],
                "raw_query": query,
                "notes": [],
                "error": str(e),
            }

