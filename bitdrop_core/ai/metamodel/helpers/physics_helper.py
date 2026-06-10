from __future__ import annotations
from typing import Any, Dict, List
import zlib
import math


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


# ------------------------------------------------------------
# RELATIVISTIC PHYSICS SOLVER (MAX 3D CORE)
# ------------------------------------------------------------
class RelativisticPhysicsSolver:
    """
    RelativisticPhysicsSolver

    Focus:
        - 1D special-relativistic problems
        - Photon rockets and mass loss
        - Energy–momentum conservation
        - Sanity checks and physical feasibility

    This solver is intentionally conservative:
        - It prefers to say "scenario is unphysical" rather than fake a number.
        - It encodes a few canonical patterns (photon rocket, fraction of rest mass energy, etc.).
    """

    def __init__(self) -> None:
        self.c = 299792458.0

    # --------------------------------------------------------
    # PUBLIC ENTRY
    # --------------------------------------------------------
    def solve(self, query: str) -> Dict[str, Any]:
        q = (query or "").lower()

        # Photon rocket style problems
        if "photon rocket" in q or ("photon" in q and "rocket" in q):
            return self._solve_photon_rocket(q)

        # Generic relativistic speed / gamma questions
        if "gamma" in q or "lorentz factor" in q:
            return self._solve_gamma_related(q)

        # Fallback: no specific pattern recognized
        return {
            "recognized": False,
            "type": "generic_relativistic",
            "summary": "No specific relativistic pattern recognized; use general energy–momentum reasoning.",
            "details": [],
        }

    # --------------------------------------------------------
    # PHOTON ROCKET HANDLING
    # --------------------------------------------------------
    def _solve_photon_rocket(self, q: str) -> Dict[str, Any]:
        """
        Handle photon rocket style questions.

        We look for phrases like:
            - "emits energy equal to its rest mass energy"
            - "emits a fraction f of its rest mass energy"
        and reason about feasibility.
        """

        details: List[str] = []
        details.append("Interpreting scenario as a 1D photon rocket in special relativity.")
        details.append("Work in the initial rest frame of the rocket: initial momentum p = 0, energy E0 = m0 c^2.")

        # Detect "equal to its rest mass energy" style phrasing
        equal_rest = "equal to its rest mass energy" in q or "equal to its rest-mass energy" in q

        # Detect "fraction of its rest mass energy" style phrasing
        fraction_keywords = [
            "fraction of its rest mass energy",
            "fraction of its rest-mass energy",
            "fraction f of its rest mass energy",
            "fraction f of its rest-mass energy",
        ]
        is_fraction = any(k in q for k in fraction_keywords)

        # Very rough fraction extraction (look for "f = 0.5" or "f=0.5" or "50%")
        f = None
        f_from_text = self._extract_fraction(q)
        if f_from_text is not None:
            f = f_from_text
            details.append(f"Detected explicit fraction of rest-mass energy: f ≈ {f:.3f}.")
        elif is_fraction:
            # If user says "fraction" but no explicit number, treat as symbolic f
            details.append("Detected a symbolic fraction f of rest-mass energy; leaving result in terms of f.")
        elif equal_rest:
            details.append("Detected phrase 'equal to its rest mass energy' (f = 1).")
            f = 1.0

        # If we have a numeric fraction f, analyze feasibility
        if f is not None:
            if f <= 0.0:
                details.append("Fraction f ≤ 0 implies no energy is emitted; final velocity v = 0.")
                return {
                    "recognized": True,
                    "type": "photon_rocket",
                    "feasible": True,
                    "fraction": f,
                    "beta": 0.0,
                    "gamma": 1.0,
                    "summary": "No energy emitted; rocket remains at rest (v = 0).",
                    "details": details,
                }

            if f >= 1.0:
                # Physically, emitting energy equal to or greater than m0 c^2 while remaining a massive rocket
                # is not possible in simple photon-rocket models: the rocket would have zero or negative rest mass.
                details.append(
                    "Emitting energy equal to or greater than the entire rest-mass energy (f ≥ 1) "
                    "is not physically consistent for a massive rocket: the rocket would be left with zero or negative rest mass."
                )
                return {
                    "recognized": True,
                    "type": "photon_rocket",
                    "feasible": False,
                    "fraction": f,
                    "summary": (
                        "The scenario 'emits energy equal to its rest mass energy' is not physically consistent "
                        "for a massive photon rocket in special relativity. The rocket cannot radiate away 100% "
                        "of its rest-mass energy and still remain a massive object."
                    ),
                    "details": details,
                }

            # For 0 < f < 1, we can give a qualitative answer:
            # The rocket accelerates to some v < c; exact closed-form depends on detailed model.
            # We provide a conservative qualitative description.
            details.append(
                "For 0 < f < 1, the rocket loses rest mass and gains kinetic energy; it reaches some v < c."
            )
            details.append(
                "A full exact expression for v(f) depends on the detailed photon-rocket model, "
                "but energy–momentum conservation guarantees v remains subluminal."
            )

            return {
                "recognized": True,
                "type": "photon_rocket",
                "feasible": True,
                "fraction": f,
                "beta": None,
                "gamma": None,
                "summary": (
                    "For a photon rocket emitting a fraction 0 < f < 1 of its rest-mass energy as photons, "
                    "the rocket accelerates to some subluminal speed v (v < c). The exact v(f) depends on the "
                    "detailed model, but energy–momentum conservation ensures the rocket remains massive and subluminal."
                ),
                "details": details,
            }

        # If we only know it is a photon rocket but no fraction is given
        details.append(
            "No explicit fraction of rest-mass energy detected; treat this as a qualitative photon-rocket problem."
        )
        details.append(
            "Use energy–momentum conservation: initial (E0 = m0 c^2, p0 = 0), final rocket + photon exhaust."
        )
        return {
            "recognized": True,
            "type": "photon_rocket",
            "feasible": True,
            "fraction": None,
            "beta": None,
            "gamma": None,
            "summary": (
                "Photon rocket scenario detected. Use energy–momentum conservation in the rocket's initial rest frame. "
                "The rocket loses rest mass and gains kinetic energy while emitting photons; its final speed remains v < c."
            ),
            "details": details,
        }

    def _extract_fraction(self, q: str) -> float | None:
        """
        Very lightweight fraction extractor:
            - looks for 'f = number'
            - looks for 'f=number'
            - looks for 'number%' patterns
        """
        q = q.replace("%", " % ")
        tokens = q.split()
        # Look for "f = x" or "f= x" or "f =x" or "f=x"
        for i, tok in enumerate(tokens):
            if tok == "f" and i + 2 < len(tokens) and tokens[i + 1] in ("=", "≈", "~"):
                try:
                    val = float(tokens[i + 2])
                    return val
                except Exception:
                    continue
            if tok.startswith("f=") or tok.startswith("f≈") or tok.startswith("f~"):
                try:
                    val_str = tok[2:]
                    val = float(val_str)
                    return val
                except Exception:
                    continue

        # Look for "number %" patterns
        for i, tok in enumerate(tokens):
            if tok == "%":
                if i > 0:
                    try:
                        val = float(tokens[i - 1])
                        return val / 100.0
                    except Exception:
                        continue
        return None

    # --------------------------------------------------------
    # GENERIC GAMMA / SPEED HANDLING
    # --------------------------------------------------------
    def _solve_gamma_related(self, q: str) -> Dict[str, Any]:
        """
        Handle generic gamma / Lorentz factor questions qualitatively.
        """
        details: List[str] = []
        details.append("Detected mention of gamma / Lorentz factor; using generic relativistic relations.")
        details.append("Core relations: gamma = 1 / sqrt(1 - v^2 / c^2), E = gamma m c^2, p = gamma m v.")

        return {
            "recognized": True,
            "type": "gamma_relation",
            "summary": (
                "Use gamma = 1 / sqrt(1 - v^2 / c^2) to relate speed v and Lorentz factor gamma. "
                "Energy and momentum follow E = gamma m c^2 and p = gamma m v."
            ),
            "details": details,
        }


# ------------------------------------------------------------
# MAIN HELPER (STRUCTURED PHYSICS REASONING, MAX 3D)
# ------------------------------------------------------------
class PhysicsHelper:
    """
    Upgraded PhysicsHelper (MAX 3D Version)

    This version produces a strict, 4-section, domain-oriented reasoning envelope
    suitable for multi-pass, 3D tensor-based thinking.

    Output format (from process):
        {
            "text": "<full structured answer>",
            "sections": ["Definitions", "Derivation", "Conditions", "Final Answer"],
            "domain": "physics",
            "valid": True,
            "raw_query": "<normalized query>",
            "entities": [...],
            "regime": "<classical|relativistic|gr|quantum|mixed>",
            "hints": [...],
            "solver": { ... optional structured solver output ... },
        }
    """

    def __init__(self) -> None:
        # Per-helper cache keyed by fast hash of normalized query
        self.cache: Dict[int, Dict[str, Any]] = {}
        self.rel_solver = RelativisticPhysicsSolver()

    # --------------------------------------------------------
    # PUBLIC INTERFACE
    # --------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Structured physics reasoning entry point.

        `lang_info` and `memory_info` are kept for compatibility and may
        be used by higher-level systems, but this helper focuses on
        building a robust scaffold for the language model.
        """
        try:
            query = (query or "").strip()
            if not query:
                return {
                    "text": "",
                    "sections": [],
                    "domain": "physics",
                    "valid": False,
                    "raw_query": "",
                    "entities": [],
                    "regime": "unknown",
                    "hints": [],
                    "solver": None,
                }

            # Normalize + limit
            norm = MicroStringStripper.clean(query)
            norm = MicroTokenLimiter.limit(norm)

            # Cache lookup
            h = MicroFastHash.h(norm)
            cached = self.cache.get(h)
            if cached is not None:
                return cached

            # Extract entities and detect regime
            entities = MicroEntityExtractor.extract(norm)
            regime = self._detect_regime(norm)
            hints = self._build_hints(norm, regime)

            # Try relativistic solver when appropriate
            solver_result: Dict[str, Any] | None = None
            if regime in ("relativistic", "mixed", "mixed_rel_gr", "mixed_rel_qm"):
                solver_result = self.rel_solver.solve(norm)

            # Build structured sections
            definitions = self._build_definitions(norm, entities, regime)
            derivation = self._build_derivation(norm, regime)
            conditions = self._build_conditions(norm, regime)
            final_answer = self._build_final_answer(norm, regime, solver_result)

            text = (
                "[1] Definitions\n" + definitions + "\n\n"
                "[2] Derivation\n" + derivation + "\n\n"
                "[3] Conditions\n" + conditions + "\n\n"
                "[4] Final Answer\n" + final_answer
            )

            envelope: Dict[str, Any] = {
                "text": text,
                "sections": [
                    "Definitions",
                    "Derivation",
                    "Conditions",
                    "Final Answer",
                ],
                "domain": "physics",
                "valid": True,
                "raw_query": norm,
                "entities": entities,
                "regime": regime,
                "hints": hints,
                "solver": solver_result,
            }

            self.cache[h] = envelope
            return envelope

        except Exception as e:
            norm = MicroStringStripper.clean(query or "")
            norm = MicroTokenLimiter.limit(norm)
            h = MicroFastHash.h(norm)
            env = {
                "text": f"[PhysicsHelperError] {e}",
                "sections": [],
                "domain": "physics",
                "valid": False,
                "raw_query": norm,
                "entities": [],
                "regime": "error",
                "hints": [],
                "solver": None,
                "error": str(e),
            }
            self.cache[h] = env
            return env

    # --------------------------------------------------------
    # REGIME DETECTION + HINTS
    # --------------------------------------------------------
    def _detect_regime(self, query: str) -> str:
        q = query.lower()

        is_rel = any(w in q for w in ["relativistic", "lorentz", "gamma", "c^2", "special relativity"])
        is_gr = any(w in q for w in ["schwarzschild", "kerr", "ergosphere", "event horizon", "beyer-lindquist", "geodesic"])
        is_qm = any(w in q for w in ["wavefunction", "schrödinger", "hilbert space", "operator", "quantum", "superposition"])
        is_em = any(w in q for w in ["maxwell", "electromagnetic", "field", "charge", "current"])
        is_newton = any(w in q for w in ["force", "mass", "acceleration", "newton", "f = ma"])

        if is_gr:
            return "gr"
        if is_rel and not is_gr:
            return "relativistic"
        if is_qm:
            return "quantum"
        if is_newton and not (is_rel or is_gr or is_qm):
            return "classical"
        if is_em and not (is_rel or is_gr or is_qm):
            return "classical"
        if is_rel and is_gr:
            return "mixed_rel_gr"
        if is_rel and is_qm:
            return "mixed_rel_qm"
        return "mixed"

    def _build_hints(self, query: str, regime: str) -> List[str]:
        q = query.lower()
        hints: List[str] = []

        # Generic invariants
        hints.append("Use energy–momentum conservation explicitly, not heuristics.")
        hints.append("Check limiting cases (low velocity, high velocity, weak field, strong field).")

        # Photon / rocket / relativistic motion
        if "photon rocket" in q or ("photon" in q and "rocket" in q):
            hints.append("Work in the initial rest frame of the rocket: initial p = 0, E = m0 c^2.")
            hints.append("Use E^2 - p^2 c^2 = m^2 c^4 for the rocket and E = p c for photons.")
            hints.append("Track mass loss explicitly: final mass m < m0, with energy carried away by photons.")
        if "photon" in q and "geodesic" in q:
            hints.append("Enforce null condition p^μ p_μ = 0 for photons.")
        if "massive" in q or "particle" in q:
            hints.append("Enforce timelike condition p^μ p_μ = -m^2 c^2 for massive particles.")

        # GR-specific
        if regime == "gr":
            hints.append("Write the metric explicitly and derive conserved quantities from Killing vectors.")
            hints.append("Use p^μ p_μ = -m^2 or 0 to constrain motion in curved spacetime.")
        # Relativistic but not GR
        if regime == "relativistic":
            hints.append("Use p = γ m v and E = γ m c^2; do not mix with classical p = m v.")
            hints.append("Check that v < c for massive particles and v = c for photons.")

        # Quantum
        if regime == "quantum":
            hints.append("Use operators and expectation values; avoid classical trajectories unless in semiclassical limit.")

        return hints

    # --------------------------------------------------------
    # INTERNAL STRUCTURED BUILDERS
    # --------------------------------------------------------
    def _build_definitions(self, query: str, entities: List[str], regime: str) -> str:
        lines: List[str] = []

        if entities:
            lines.append("• Key named entities detected: " + ", ".join(entities) + ".")

        lines.append("• List all physical quantities mentioned (e.g., m0, m, v, E, p, L, Q, r, t).")
        lines.append("• Define each symbol explicitly (e.g., m0 = initial rest mass, m = final rest mass, v = velocity).")
        lines.append("• Specify the physical regime: classical, relativistic, general relativistic, or quantum.")
        lines.append("• State the frame of reference used (e.g., initial rest frame of the rocket, lab frame, asymptotic observer).")
        lines.append("• Identify whether the system involves massive particles, massless particles (photons), or fields.")
        lines.append("• List any stated or implied conservation laws (energy, momentum, angular momentum, charge).")

        if regime == "relativistic":
            lines.append("• Note that energy and momentum must satisfy E^2 - p^2 c^2 = m^2 c^4 for massive bodies.")
        if regime == "gr":
            lines.append("• Identify the spacetime (e.g., Schwarzschild, Kerr) and coordinates (e.g., Boyer–Lindquist).")
        if regime == "quantum":
            lines.append("• Identify the Hilbert space, operators, and observables relevant to the problem.")

        return "\n".join(lines)

    def _build_derivation(self, query: str, regime: str) -> str:
        lines: List[str] = []

        lines.append("• Write down the governing equations for the system (e.g., Newton's laws, relativistic energy–momentum, geodesic equation, Maxwell, Schrödinger).")
        lines.append("• Reduce the problem to the relevant degrees of freedom (e.g., radial motion, axial motion, 1D rocket motion).")

        if regime == "relativistic" or "photon rocket" in query.lower():
            lines.append("• Work in the initial rest frame when appropriate: initial momentum p = 0, initial energy E = m0 c^2.")
            lines.append("• For a photon rocket, write conservation of energy and momentum between the rocket and emitted photons.")
            lines.append("• Use E_rocket^2 - p_rocket^2 c^2 = m^2 c^4 and E_photon = p_photon c to relate mass loss, velocity, and exhaust energy.")
            lines.append("• Solve for v as a function of the fraction f of rest-mass energy converted to photons, ensuring v < c for massive rockets.")

        if regime == "gr":
            lines.append("• Write the line element and derive conserved quantities from Killing vectors (e.g., energy E, angular momentum L).")
            lines.append("• Construct an effective potential or radial function to analyze turning points or stable orbits.")
        if regime == "quantum":
            lines.append("• Write the appropriate wave equation or Hamiltonian and identify conserved quantities or symmetries.")

        lines.append("• Apply boundary or initial conditions explicitly (e.g., initial rest state, asymptotic behavior).")
        lines.append("• Simplify the resulting equations to isolate the physically meaningful quantity (e.g., v(f), critical radius, threshold energy).")
        lines.append("• Ensure each step respects the chosen regime and does not mix incompatible frameworks (e.g., classical p = m v with relativistic E = γ m c^2).")

        return "\n".join(lines)

    def _build_conditions(self, query: str, regime: str) -> str:
        lines: List[str] = []

        lines.append("• State all assumptions clearly (e.g., test particle, no backreaction, isolated system, no external fields).")
        lines.append("• Enforce relevant invariants (e.g., E^2 - p^2 c^2 = m^2 c^4 for massive bodies, E = p c for photons).")
        lines.append("• Enforce conservation laws used in the derivation (energy, momentum, angular momentum, charge).")
        lines.append("• Specify the allowed domain of variables (e.g., 0 ≤ f ≤ 1, v < c for massive rockets, r > horizon radius in GR).")
        lines.append("• Clarify whether the result is frame-dependent or invariant (e.g., energy measurements vs causal structure).")
        lines.append("• If approximations are used (e.g., weak field, low velocity, small parameter expansions), state them explicitly and check their consistency.")

        if regime == "relativistic":
            lines.append("• Check that the solution reduces to the classical limit at low velocities (v ≪ c).")
            lines.append("• Check that the solution behaves correctly as v → c (e.g., γ → ∞, mass loss constraints).")
        if regime == "gr":
            lines.append("• Ensure that the solution respects causal structure (e.g., no superluminal motion, horizons not crossed in forbidden ways).")
        if regime == "quantum":
            lines.append("• Ensure normalization and probability conservation where applicable.")

        return "\n".join(lines)

    def _build_final_answer(
        self,
        query: str,
        regime: str,
        solver_result: Dict[str, Any] | None,
    ) -> str:
        lines: List[str] = []

        # If we have a structured solver result, surface it first
        if solver_result and solver_result.get("recognized"):
            summary = solver_result.get("summary", "").strip()
            if summary:
                lines.append("• Solver conclusion: " + summary)
            feasible = solver_result.get("feasible")
            if feasible is False:
                lines.append("• The scenario is flagged as physically inconsistent under special relativity.")
            frac = solver_result.get("fraction", None)
            if frac is not None:
                lines.append(f"• Fraction of rest-mass energy emitted as photons: f ≈ {frac:.3f}.")
            beta = solver_result.get("beta", None)
            gamma = solver_result.get("gamma", None)
            if beta is not None:
                lines.append(f"• Dimensionless speed estimate: β = v / c ≈ {beta:.6f}.")
            if gamma is not None:
                lines.append(f"• Lorentz factor estimate: γ ≈ {gamma:.6f}.")
            details = solver_result.get("details", [])
            if details:
                lines.append("• Key reasoning steps from solver:")
                for d in details:
                    lines.append("  - " + d)

        # Generic final-answer guidance
        lines.append("• State the final result in a single, explicit equation or condition (e.g., v(f) = ..., r_crit = ...).")
        lines.append("• Directly answer each sub-question posed in the prompt (e.g., whether a given speed is reachable, what fraction f is required).")
        lines.append("• If the scenario is physically impossible or inconsistent with invariants, state that clearly and explain why.")
        lines.append("• Avoid vague language; commit to explicit yes/no or inequality statements when the physics allows it.")
        lines.append("• Summarize the physical interpretation of the result in one or two precise sentences (e.g., why efficiency drops as v → c, why orbits are stable/unstable).")
        lines.append("• Mention limiting behavior (e.g., low-velocity limit, ultra-relativistic limit, near-horizon behavior) to show consistency.")

        return "\n".join(lines)


# ------------------------------------------------------------
# 3D PHYSICS HELPER (MAXED, BACKWARD-COMPATIBLE)
# ------------------------------------------------------------
class PhysicsHelper3D:
    """
    3D PhysicsHelper:
        • Reuses PhysicsHelper core logic
        • Adds 3D grids of queries: [D][H][W]
        • Per-cell physics reasoning envelope
        • Cache amplification across 3D space
    """

    def __init__(self) -> None:
        self.helper = PhysicsHelper()

    def process_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[Dict[str, Any]]]]:
        depth = len(queries_3d)
        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = queries_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for q in row:
                    row_out.append(self.helper.process(q, lang_info, memory_info))
                plane_out.append(row_out)
            out.append(plane_out)

        return out

    def domain_3d(
        self,
        queries_3d: List[List[List[str]]],
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> List[List[List[str]]]:
        envelopes_3d = self.process_3d(queries_3d, lang_info, memory_info)
        depth = len(envelopes_3d)
        out: List[List[List[str]]] = []

        for d in range(depth):
            plane = envelopes_3d[d]
            plane_out: List[List[str]] = []
            for row in plane:
                row_out: List[str] = []
                for env in row:
                    row_out.append(env.get("domain", "physics"))
                plane_out.append(row_out)
            out.append(plane_out)

        return out



