from __future__ import annotations
import ast
import os
import time
import hashlib
import concurrent.futures
from typing import Dict, Any, List, Optional, Callable, Tuple


class SelfAuditEngineV4:
    """
    SelfAuditEngine V4 — 3D‑MAX, Optimized Code‑Introspection + Patch Suggestion Engine.

    Semantics:
        • 1D: audit() over a single root_path (backward‑compatible)
        • 2D: audit_batch() over a list of root_paths
        • 3D: audit_3d() over a 3D tensor of root_paths/file‑groups
          (each cell is an independent audit unit)
    """

    def __init__(
        self,
        root_path: str,
        advisor: Optional[Callable[[Dict[str, Any]], List[str]]] = None,
    ) -> None:
        self.root_path = os.path.abspath(root_path)
        self.advisor = advisor

    # ------------------------------------------------------------
    # FILE DISCOVERY / READING / AST
    # ------------------------------------------------------------
    def _list_python_files(self, root: Optional[str] = None) -> List[str]:
        base_root = os.path.abspath(root or self.root_path)
        return [
            os.path.join(base, n)
            for base, _, names in os.walk(base_root)
            for n in names
            if n.endswith(".py")
        ]

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
        return 1 + sum(
            isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With))
            for node in ast.walk(tree)
        )

    def _cognitive_complexity(self, tree: Optional[ast.AST]) -> int:
        if tree is None:
            return 0
        score = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                score += len(node.body)
            elif isinstance(node, ast.Call):
                score += 1
        return score

    # ------------------------------------------------------------
    # IMPORTS / DEPENDENCIES
    # ------------------------------------------------------------
    def _extract_imports(self, tree: Optional[ast.AST]) -> List[str]:
        if tree is None:
            return []
        imports: List[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(n.name for n in node.names)
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

        for n in graph:
            if visited.get(n, 0) == 0:
                dfs(n, [])
        return cycles

    # ------------------------------------------------------------
    # DEAD CODE / SECURITY / SLOW PATTERNS
    # ------------------------------------------------------------
    def _detect_dead_code(self, code: str) -> List[str]:
        lines = code.splitlines()
        return [
            f"Line {i+1}: 'pass' may indicate incomplete logic"
            for i, line in enumerate(lines)
            if "pass" in line and "#" not in line
        ] + [
            f"Line {i+1}: TODO/FIXME found"
            for i, line in enumerate(lines)
            if "TODO" in line or "FIXME" in line
        ]

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
        return [group for group in buckets.values() if len(group) > 1]

    # ------------------------------------------------------------
    # ORCHESTRATOR / GPU HINTS
    # ------------------------------------------------------------
    def _orchestrator_hints(self, path: str, code: str, imports: List[str]) -> List[str]:
        hints: List[str] = []
        lower = path.lower()

        if "orchestrator" in lower or "router" in lower:
            if "async" not in code and "await" not in code:
                hints.append("Orchestrator/router is synchronous — consider async for helper/model calls")
            if "timeout" not in code and "timeout_ms" not in code:
                hints.append("No explicit timeouts in orchestrator — helpers may hang under load")

        if "torch" in imports and "cuda" not in code and "to(" not in code:
            hints.append("Torch imported but no explicit GPU routing — consider .to('cuda') for heavy ops")

        return hints

    # ------------------------------------------------------------
    # PATCH SUGGESTIONS
    # ------------------------------------------------------------
    def _patch_suggestions_for_file(self, info: Dict[str, Any]) -> List[str]:
        suggestions: List[str] = []

        if info["cyclomatic_complexity"] > 40 or info["cognitive_complexity"] > 80:
            suggestions.append("Refactor: split large functions/modules into smaller units to reduce complexity.")
        if info["dead_code"]:
            suggestions.append("Cleanup: remove or implement dead/incomplete code (pass/TODO/FIXME).")
        if info["slow_patterns"]:
            suggestions.append("Optimize: address slow patterns (non‑streaming generate, manual loops).")
        if info["security_flags"]:
            suggestions.append("Harden: review and mitigate security‑sensitive constructs (eval/exec/pickle/subprocess).")
        if info["orchestrator_hints"]:
            suggestions.extend(info["orchestrator_hints"])

        if self.advisor:
            try:
                extra = self.advisor(info) or []
                suggestions.extend(extra)
            except Exception:
                pass

        return suggestions

    # ------------------------------------------------------------
    # PER‑FILE ANALYSIS
    # ------------------------------------------------------------
    def _analyze_file(self, path: str) -> Tuple[str, Dict[str, Any], List[str], str]:
        code = self._read_file(path)
        tree = self._parse_ast(code)

        imports = self._extract_imports(tree)
        dead = self._detect_dead_code(code)
        slow = self._slow_patterns(code)
        sec = self._security_flags(code)
        orch = self._orchestrator_hints(path, code, imports)

        info: Dict[str, Any] = {
            "path": path,
            "cyclomatic_complexity": self._cyclomatic_complexity(tree),
            "cognitive_complexity": self._cognitive_complexity(tree),
            "imports": imports,
            "dead_code": dead,
            "slow_patterns": slow,
            "security_flags": sec,
            "orchestrator_hints": orch,
        }
        info["patch_suggestions"] = self._patch_suggestions_for_file(info)

        return path, info, imports, self._hash_code(code)

    # ------------------------------------------------------------
    # CORE AUDIT FOR A SINGLE ROOT / FILE‑GROUP
    # ------------------------------------------------------------
    def _audit_root(self, root: Optional[str] = None) -> Dict[str, Any]:
        start = time.time()

        py_files = self._list_python_files(root)
        file_imports: Dict[str, List[str]] = {}
        file_hashes: Dict[str, str] = {}
        files_info: List[Dict[str, Any]] = []

        with concurrent.futures.ThreadPoolExecutor() as ex:
            for path, info, imports, h in ex.map(self._analyze_file, py_files):
                files_info.append(info)
                file_imports[path] = imports
                file_hashes[path] = h

        dep_graph = self._build_dependency_graph(file_imports)
        cycles = self._detect_cycles(dep_graph)
        duplicates = self._detect_duplicate_files(file_hashes)

        summary = {
            "total_files": len(py_files),
            "high_complexity_files": sum(f["cyclomatic_complexity"] > 40 for f in files_info),
            "files_with_dead_code": sum(bool(f["dead_code"]) for f in files_info),
            "files_with_slow_patterns": sum(bool(f["slow_patterns"]) for f in files_info),
            "files_with_security_flags": sum(bool(f["security_flags"]) for f in files_info),
            "files_with_orchestrator_hints": sum(bool(f["orchestrator_hints"]) for f in files_info),
            "dependency_cycles": len(cycles),
            "duplicate_file_groups": len(duplicates),
        }

        slow_candidates: List[Dict[str, Any]] = []
        for f in files_info:
            if (
                f["slow_patterns"]
                or f["orchestrator_hints"]
                or f["dead_code"]
                or f["cyclomatic_complexity"] > 40
                or f["cognitive_complexity"] > 80
            ):
                severity = (
                    len(f["slow_patterns"]) * 3
                    + len(f["orchestrator_hints"]) * 2
                    + len(f["dead_code"])
                    + (1 if f["cyclomatic_complexity"] > 40 else 0)
                    + (1 if f["cognitive_complexity"] > 80 else 0)
                )
                slow_candidates.append({**f, "severity": severity})

        slow_candidates.sort(key=lambda x: x["severity"], reverse=True)

        return {
            "ok": True,
            "root": os.path.abspath(root or self.root_path),
            "files": files_info,
            "summary": summary,
            "dependency_cycles": cycles,
            "duplicate_files": duplicates,
            "pipeline_slowdown": {
                "slow_files": [c["path"] for c in slow_candidates],
                "details": slow_candidates,
            },
            "self_reflection": [
                "Some modules exhibit high complexity — refactoring into smaller components would improve maintainability.",
                "Dead code and TODO/FIXME markers indicate unfinished logic that should be completed or removed.",
                "Non‑streaming and manual loop patterns suggest performance bottlenecks under load.",
                "Security‑sensitive constructs require careful review to avoid unsafe behavior.",
                "Orchestrator and helper‑mesh hints point to opportunities for better async, timeout, and GPU routing.",
            ],
            "latency_ms": int((time.time() - start) * 1000),
        }

    # ------------------------------------------------------------
    # MAIN AUDIT (1D, backward‑compatible)
    # ------------------------------------------------------------
    def audit(self, *_, **__) -> Dict[str, Any]:
        return self._audit_root(self.root_path)

    # ------------------------------------------------------------
    # BATCH AUDIT (2D list of roots)
    # ------------------------------------------------------------
    def audit_batch(self, roots: List[str]) -> List[Dict[str, Any]]:
        return [SelfAuditEngineV4(root, advisor=self.advisor)._audit_root(root) for root in roots]

    # ------------------------------------------------------------
    # 3D‑MAX AUDIT (tensor‑style)
    # ------------------------------------------------------------
    def audit_3d(
        self,
        roots_3d: List[List[List[str]]],
    ) -> List[List[List[Dict[str, Any]]]]:
        """
        3D‑MAX audit:
            roots_3d[d][h][w] -> same shape of audit result dicts.

        Each cell is treated as an independent root/file‑group.
        """
        depth = len(roots_3d)
        if depth == 0:
            return []

        out: List[List[List[Dict[str, Any]]]] = []

        for d in range(depth):
            plane = roots_3d[d]
            plane_out: List[List[Dict[str, Any]]] = []
            for row in plane:
                row_out: List[Dict[str, Any]] = []
                for root in row:
                    engine = SelfAuditEngineV4(root, advisor=self.advisor)
                    row_out.append(engine._audit_root(root))
                plane_out.append(row_out)
            out.append(plane_out)

        return out






