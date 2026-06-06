from __future__ import annotations
import ast
import os
import time
import hashlib
from typing import Dict, Any, List, Optional, Callable


class SelfAuditEngineV4:
    """
    SelfAuditEngine V4 — Autonomous Code‑Introspection + Patch Suggestion Engine

    Capabilities:
        • Static AST analysis
        • Complexity scoring (cyclomatic + cognitive)
        • Dead code + TODO/FIXME detection
        • Slow‑pattern detection
        • Security linting (eval/exec/dangerous imports)
        • Dependency graph + cycle detection
        • Duplicate‑logic detection via hashing
        • Orchestrator + helper‑mesh optimization hints
        • GPU/CPU routing warnings
        • High‑level patch suggestions (rule‑based, advisor‑aware)
        • Full codebase health summary + self‑reflection
    """

    def __init__(
        self,
        root_path: str,
        advisor: Optional[Callable[[Dict[str, Any]], List[str]]] = None,
    ) -> None:
        """
        root_path: project root to scan.
        advisor: optional callable that can generate extra suggestions
                 given the per‑file analysis dict.
        """
        self.root_path = os.path.abspath(root_path)
        self.advisor = advisor

    # ------------------------------------------------------------
    # FILE DISCOVERY / READING / AST
    # ------------------------------------------------------------
    def _list_python_files(self) -> List[str]:
        files: List[str] = []
        for base, _, names in os.walk(self.root_path):
            for n in names:
                if n.endswith(".py"):
                    files.append(os.path.join(base, n))
        return files

    def _read_file(self, path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            return ""

    def _parse_ast(self, code: str) -> Optional[ast.AST]:
        try:
            return ast.parse(code)
        except Exception:
            return None

    # ------------------------------------------------------------
    # COMPLEXITY
    # ------------------------------------------------------------
    def _cyclomatic_complexity(self, tree: Optional[ast.AST]) -> int:
        if tree is None:
            return 0
        complexity = 1
        for node in ast.walk(tree):
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                complexity += 1
        return complexity

    def _cognitive_complexity(self, tree: Optional[ast.AST]) -> int:
        if tree is None:
            return 0
        score = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                score += len(node.body)
            if isinstance(node, ast.Call):
                score += 1
        return score

    # ------------------------------------------------------------
    # IMPORTS / DEPENDENCIES
    # ------------------------------------------------------------
    def _extract_imports(self, tree: Optional[ast.AST]) -> List[str]:
        imports: List[str] = []
        if tree is None:
            return imports
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    imports.append(n.name)
            elif isinstance(node, ast.ImportFrom):
                imports.append(node.module or "")
        return imports

    def _build_dependency_graph(self, file_imports: Dict[str, List[str]]) -> Dict[str, List[str]]:
        return file_imports

    def _detect_cycles(self, graph: Dict[str, List[str]]) -> List[str]:
        cycles: List[str] = []
        visited: Dict[str, int] = {}

        def dfs(node: str, stack: List[str]) -> None:
            state = visited.get(node, 0)
            if state == 1:
                cycles.append(" -> ".join(stack + [node]))
                return
            if state == 2:
                return
            visited[node] = 1
            for dep in graph.get(node, []):
                dfs(dep, stack + [node])
            visited[node] = 2

        for n in graph.keys():
            if visited.get(n, 0) == 0:
                dfs(n, [])
        return cycles

    # ------------------------------------------------------------
    # DEAD CODE / SECURITY / SLOW PATTERNS
    # ------------------------------------------------------------
    def _detect_dead_code(self, code: str) -> List[str]:
        lines = code.splitlines()
        dead: List[str] = []
        for i, line in enumerate(lines):
            if "pass" in line and "#" not in line:
                dead.append(f"Line {i+1}: 'pass' may indicate incomplete logic")
            if "TODO" in line or "FIXME" in line:
                dead.append(f"Line {i+1}: TODO/FIXME found")
        return dead

    def _security_flags(self, code: str) -> List[str]:
        flags: List[str] = []
        if "eval(" in code:
            flags.append("Use of eval() detected — dangerous for untrusted input")
        if "exec(" in code:
            flags.append("Use of exec() detected — dangerous for untrusted input")
        if "pickle.loads" in code:
            flags.append("pickle.loads detected — unsafe for untrusted input")
        if "subprocess" in code:
            flags.append("subprocess usage detected — ensure argument sanitization")
        return flags

    def _slow_patterns(self, code: str) -> List[str]:
        flags: List[str] = []
        if "time.sleep" in code:
            flags.append("Blocking sleep detected — consider async/await or non‑blocking timers")
        if ".generate(" in code and "stream=False" in code:
            flags.append("Model generate() with stream=False — may cause latency spikes")
        if "for " in code and "in range(" in code and ".append(" in code:
            flags.append("Manual list building in loop — consider list comprehensions")
        return flags

    # ------------------------------------------------------------
    # DUPLICATE LOGIC
    # ------------------------------------------------------------
    def _hash_code(self, code: str) -> str:
        return hashlib.sha256(code.encode("utf-8")).hexdigest()

    def _detect_duplicate_files(self, file_hashes: Dict[str, str]) -> List[List[str]]:
        buckets: Dict[str, List[str]] = {}
        for path, h in file_hashes.items():
            buckets.setdefault(h, []).append(path)
        return [paths for paths in buckets.values() if len(paths) > 1]

    # ------------------------------------------------------------
    # ORCHESTRATOR / HELPER‑MESH / GPU HINTS
    # ------------------------------------------------------------
    def _orchestrator_hints(self, path: str, code: str, imports: List[str]) -> List[str]:
        hints: List[str] = []
        lower_path = path.lower()

        if "orchestrator" in lower_path or "router" in lower_path:
            if "async" not in code and "await" not in code:
                hints.append("Orchestrator/router is synchronous — consider async for helper/model calls")
            if "timeout" not in code and "timeout_ms" not in code:
                hints.append("No explicit timeouts in orchestrator — helpers may hang under load")

        if "helper_mesh" in lower_path or "mesh" in lower_path:
            if "priority" not in code:
                hints.append("Helper mesh without explicit priorities — consider priority‑based scheduling")

        if "torch" in imports and "cuda" not in code and "to(" not in code:
            hints.append("Torch imported but no explicit GPU routing — consider .to('cuda') for heavy ops")

        return hints

    # ------------------------------------------------------------
    # PATCH SUGGESTIONS (RULE‑BASED + ADVISOR)
    # ------------------------------------------------------------
    def _patch_suggestions_for_file(self, info: Dict[str, Any]) -> List[str]:
        suggestions: List[str] = []

        cyclo = info.get("cyclomatic_complexity", 0)
        cog = info.get("cognitive_complexity", 0)
        dead = info.get("dead_code", [])
        slow = info.get("slow_patterns", [])
        sec = info.get("security_flags", [])
        orch = info.get("orchestrator_hints", [])

        if cyclo > 40 or cog > 80:
            suggestions.append("Refactor: split large functions/modules into smaller units to reduce complexity.")
        if dead:
            suggestions.append("Cleanup: remove or implement dead/incomplete code (pass/TODO/FIXME).")
        if slow:
            suggestions.append("Optimize: address slow patterns (blocking sleep, non‑streaming generate, manual loops).")
        if sec:
            suggestions.append("Harden: review and mitigate security‑sensitive constructs (eval/exec/pickle/subprocess).")
        if orch:
            suggestions.extend(orch)

        # External advisor hook (e.g., LLM‑based) if provided
        if self.advisor is not None:
            try:
                extra = self.advisor(info) or []
                suggestions.extend(extra)
            except Exception:
                pass

        return suggestions

    # ------------------------------------------------------------
    # MAIN AUDIT
    # ------------------------------------------------------------
    def audit(self) -> Dict[str, Any]:
        start = time.time()

        report: Dict[str, Any] = {
            "ok": True,
            "files": [],
            "summary": {},
            "latency_ms": 0,
            "self_reflection": [],
            "dependency_cycles": [],
            "duplicate_files": [],
        }

        py_files = self._list_python_files()
        file_imports: Dict[str, List[str]] = {}
        file_hashes: Dict[str, str] = {}

        for path in py_files:
            code = self._read_file(path)
            tree = self._parse_ast(code)

            cyclo = self._cyclomatic_complexity(tree)
            cog = self._cognitive_complexity(tree)
            imports = self._extract_imports(tree)
            dead = self._detect_dead_code(code)
            slow = self._slow_patterns(code)
            sec = self._security_flags(code)
            orch_hints = self._orchestrator_hints(path, code, imports)

            file_imports[path] = imports
            file_hashes[path] = self._hash_code(code)

            file_info: Dict[str, Any] = {
                "path": path,
                "cyclomatic_complexity": cyclo,
                "cognitive_complexity": cog,
                "imports": imports,
                "dead_code": dead,
                "slow_patterns": slow,
                "security_flags": sec,
                "orchestrator_hints": orch_hints,
            }

            file_info["patch_suggestions"] = self._patch_suggestions_for_file(file_info)

            report["files"].append(file_info)

        # Dependency graph + cycles
        dep_graph = self._build_dependency_graph(file_imports)
        cycles = self._detect_cycles(dep_graph)
        report["dependency_cycles"] = cycles

        # Duplicate files
        duplicates = self._detect_duplicate_files(file_hashes)
        report["duplicate_files"] = duplicates

        # Summary
        report["summary"] = {
            "total_files": len(py_files),
            "high_complexity_files": sum(1 for f in report["files"] if f["cyclomatic_complexity"] > 40),
            "files_with_dead_code": sum(1 for f in report["files"] if f["dead_code"]),
            "files_with_slow_patterns": sum(1 for f in report["files"] if f["slow_patterns"]),
            "files_with_security_flags": sum(1 for f in report["files"] if f["security_flags"]),
            "files_with_orchestrator_hints": sum(1 for f in report["files"] if f["orchestrator_hints"]),
            "dependency_cycles": len(cycles),
            "duplicate_file_groups": len(duplicates),
        }

        # Self‑reflection (high‑level)
        report["self_reflection"] = [
            "Some modules exhibit high complexity — refactoring into smaller components would improve maintainability.",
            "Dead code and TODO/FIXME markers indicate unfinished logic that should be completed or removed.",
            "Blocking and non‑streaming patterns suggest performance bottlenecks under load.",
            "Security‑sensitive constructs require careful review to avoid unsafe behavior.",
            "Orchestrator and helper‑mesh hints point to opportunities for better async, timeout, and GPU routing.",
        ]

        report["latency_ms"] = int((time.time() - start) * 1000)
        return report


