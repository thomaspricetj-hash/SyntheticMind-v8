

from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple
import re
import os
import ast


class CodeCorrectionHelper:
    """
    Ultra‑Pro Multilingual Code Correction + Self‑Audit Engine
    ----------------------------------------------------------
    • Exposes process(query, lang_info, memory_info) for HelperMesh
    • Detects hallucinated / invalid code patterns
    • Injects canonical, professional patterns (especially plugin loaders)
    • Self‑audits the codebase via AST (structure, docstrings, syntax)
    """

    __slots__ = ()

    # ------------------------------------------------------------
    # Mesh entrypoint
    # ------------------------------------------------------------
    def process(
        self,
        query: str,
        lang_info: Dict[str, Any],
        memory_info: Dict[str, Any],
    ) -> Dict[str, Any]:
        lowered = (query or "").lower()

        # Self‑audit trigger (introspective mode)
        if (
            "self audit" in lowered
            or "self-audit" in lowered
            or "introspect codebase" in lowered
            or "scan my codebase" in lowered
        ):
            root_dir = "."
            if isinstance(memory_info, dict):
                root_dir = memory_info.get("root_dir", root_dir)
            report = self.self_audit(root_dir=root_dir)
            return {
                "detected": True,
                "intent": "self_audit",
                "root_dir": report["root_dir"],
                "summary": report["summary"],
                "files_scanned": report["files_scanned"],
                "functions": report["functions"],
                "classes": report["classes"],
                "issues": report["issues"],
            }

        # Prefer code blocks from lang_info if present
        code_blocks: List[str] = []
        if isinstance(lang_info, dict):
            cb = lang_info.get("code_blocks")
            if isinstance(cb, list):
                code_blocks = [str(b) for b in cb]

        # Fallback: extract fenced code from query
        if not code_blocks and "```" in query:
            fenced = re.findall(r"```(?:\w+)?\n(.*?)```", query, re.DOTALL)
            code_blocks = [b.strip() for b in fenced if b.strip()]

        # If no code, nothing to correct
        if not code_blocks:
            return {
                "detected": False,
                "intent": "code_correction",
                "language": (lang_info.get("language") if isinstance(lang_info, dict) else "unknown") or "unknown",
                "code_blocks": [],
                "notes": [],
            }

        notes: List[str] = []
        for block in code_blocks:
            notes.extend(self.correct(block))

        return {
            "detected": bool(notes),
            "intent": "code_correction",
            "language": (lang_info.get("language") if isinstance(lang_info, dict) else "unknown") or "unknown",
            "code_blocks": code_blocks,
            "notes": notes,
        }

    # ------------------------------------------------------------
    # Self‑audit subsystem
    # ------------------------------------------------------------
    def self_audit(self, root_dir: str = ".") -> Dict[str, Any]:
        """
        Introspect the codebase rooted at `root_dir`:
        • Scans Python files
        • Parses ASTs
        • Collects functions, classes
        • Flags missing docstrings and parse errors
        """
        root_dir = os.path.abspath(root_dir)
        report: Dict[str, Any] = {
            "root_dir": root_dir,
            "files_scanned": 0,
            "functions": [],   # List[Dict[name,file,lineno]]
            "classes": [],     # List[Dict[name,file,lineno]]
            "issues": [],      # List[str]
        }

        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue

                full_path = os.path.join(dirpath, fname)
                report["files_scanned"] += 1

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        source = f.read()
                    tree = ast.parse(source, filename=full_path)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            func_info = {
                                "name": node.name,
                                "file": full_path,
                                "lineno": node.lineno,
                            }
                            report["functions"].append(func_info)
                            if not ast.get_docstring(node):
                                report["issues"].append(
                                    f"Missing docstring in function '{node.name}' ({full_path}:{node.lineno})"
                                )
                        elif isinstance(node, ast.ClassDef):
                            class_info = {
                                "name": node.name,
                                "file": full_path,
                                "lineno": node.lineno,
                            }
                            report["classes"].append(class_info)
                            if not ast.get_docstring(node):
                                report["issues"].append(
                                    f"Missing docstring in class '{node.name}' ({full_path}:{node.lineno})"
                                )

                except SyntaxError as e:
                    report["issues"].append(
                        f"SyntaxError in {full_path}: {e.msg} (line {e.lineno})"
                    )
                except Exception as e:
                    report["issues"].append(
                        f"Failed to parse {full_path}: {e}"
                    )

        report["summary"] = (
            f"Scanned {report['files_scanned']} files, "
            f"found {len(report['functions'])} functions and {len(report['classes'])} classes, "
            f"{len(report['issues'])} issues."
        )
        return report

    # ------------------------------------------------------------
    # Core correction logic
    # ------------------------------------------------------------
    @staticmethod
    def correct(code: str) -> List[str]:
        notes: List[str] = []

        # ============================================================
        # 1. Hallucinated variables / syntax (universal)
        # ============================================================
        if re.search(r"\bextradata\b|\bendpoint\b|\bvalidate\b|\bexecute=False\b", code):
            notes.append("Correction: Remove hallucinated variables. Use only real, defined variables.")

        if re.search(r"[A-Za-z0-9_]+\s*endpoint=", code):
            notes.append("Correction: 'endpoint=' is hallucinated. Replace with real function arguments.")

        if "os.path endpoint" in code:
            notes.append("Correction: 'os.path endpoint' is invalid. Use os.path.join().")

        if "inflinker" in code or "baseinflinker" in code:
            notes.append("Correction: 'inflinker' is hallucinated. Use a real path string or variable name.")

        # ============================================================
        # 2. Broken main guard (Python)
        # ============================================================
        if "__main__0" in code or "__main__0__" in code:
            notes.append("Python Correction: Use correct main guard: if __name__ == '__main__':")

        # ============================================================
        # 3. Fake context manager on run() (Python)
        # ============================================================
        if "with plugin.run()" in code or "with module.run()" in code:
            notes.append("Python Correction: run() is not a context manager. Call plugin.run() directly.")

        # ============================================================
        # 4. Wrong importlib usage (Python)
        # ============================================================
        if "importlib.import_module" in code and ".py" in code:
            notes.append("Python Correction: import_module cannot load .py paths directly; use spec_from_file_location.")

        if "importlib.import_module" in code and "self.base_path" in code:
            notes.append("Python Correction: import_module expects a package path, not a filesystem path. Use spec_from_file_location for /modules.")

        if "import_module(f" in code and "plugin" in code:
            notes.append("Python Correction: Avoid f-strings with filesystem paths in import_module. Use spec_from_file_location.")

        # ============================================================
        # 5. Wrong plugin dict / structure (Python)
        # ============================================================
        if "for name, (run_func, deps) in plugins.items()" in code:
            notes.append("Python Correction: plugins[name] should be the module object, not a (run, deps) tuple.")

        if "plugins[p][0]" in code or "plugins[p][1]" in code:
            notes.append("Python Correction: Do not index plugin modules. Store modules directly and access attributes.")

        # ============================================================
        # 6. Wrong dependency sorting / logic (Python)
        # ============================================================
        if "sorted(" in code and "dependencies" in code:
            notes.append("Python Correction: Dependency order requires DFS topological sort, not sorted().")

        if "lambda p:" in code and "dependencies" in code:
            notes.append("Python Correction: Sorting by dependency list is incorrect. Use DFS with cycle detection.")

        if "dependencies or not dependencies" in code:
            notes.append("Python Correction: Invalid dependency check. Iterate dependencies[name] explicitly in DFS.")

        # ============================================================
        # 7. Missing run() validation (Python)
        # ============================================================
        if "run(" not in code and "callable" not in code:
            notes.append("Python Correction: Validate plugins with hasattr(module, 'run') and callable(module.run).")

        # ============================================================
        # 8. Missing cycle detection (Python / universal)
        # ============================================================
        if "cycle" not in code.lower() and "detect" not in code.lower():
            notes.append("Correction: Add cycle detection using a 'visiting' set in DFS.")

        # ============================================================
        # 9. Invalid dependency extraction (Python)
        # ============================================================
        if "os.getenv('PLUGINS')" in code or "env_plugins" in code:
            notes.append("Python Correction: Dependencies must come from plugin metadata, not environment variables.")

        # ============================================================
        # 10. Invalid execution logic (Python)
        # ============================================================
        if "next_to_run" in code and "plugins.keys()" in code:
            notes.append("Python Correction: Execution logic is invalid. Resolve dependencies via DFS, then run.")

        if "del plugins" in code:
            notes.append("Python Correction: Do not delete plugins during execution. Track executed plugins in a set.")

        # ============================================================
        # 11. Invalid assumptions about run() (Python)
        # ============================================================
        if "run returns" in code or ("run()" in code and "context" in code):
            notes.append("Python Correction: run() should be a simple callable, not a context manager or special type.")

        # ============================================================
        # 12. Canonical plugin loader pattern (Python)
        # ============================================================
        notes.append("Canonical Plugin Loader Pattern (Python):")
        notes.append(
            "Use:\n"
            "spec = importlib.util.spec_from_file_location(name, path)\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
            "if not hasattr(module, 'run') or not callable(module.run): raise\n"
            "dependencies = getattr(module, 'dependencies', [])\n"
            "execute with DFS + cycle detection"
        )

        # ============================================================
        # 13. Canonical dependency execution pattern (Python / universal)
        # ============================================================
        notes.append("Canonical Dependency Execution Pattern:")
        notes.append(
            "Use DFS:\n"
            "executed = set()\n"
            "visiting = set()\n"
            "def execute(name):\n"
            "    if name in executed: return\n"
            "    if name in visiting: raise RuntimeError('Cycle detected')\n"
            "    visiting.add(name)\n"
            "    for dep in dependencies[name]: execute(dep)\n"
            "    visiting.remove(name)\n"
            "    executed.add(name)\n"
            "    plugins[name].run()"
        )

        # ============================================================
        # 14. Canonical task scheduler pattern (Python / universal)
        # ============================================================
        notes.append("Canonical Task Scheduler Pattern:")
        notes.append(
            "Use register_task(name, func, deps=[])\n"
            "Store tasks in a dict: tasks[name] = {'func': func, 'deps': deps}\n"
            "Use DFS for dependency resolution\n"
            "Detect cycles with a visiting set\n"
            "Execute tasks in topological order"
        )

        # ============================================================
        # 15. JavaScript / TypeScript corrections
        # ============================================================
        if "require(" in code and "import " in code:
            notes.append("JS/TS Correction: Do not mix require() and import. Use a single module system.")

        if "module.exports" in code and "export " in code:
            notes.append("JS/TS Correction: Do not mix CommonJS and ES Modules in the same file.")

        if "var " in code:
            notes.append("JS/TS Correction: Avoid 'var'. Prefer 'let' or 'const' for block scoping.")

        notes.append("Canonical Plugin Pattern (JS/TS):")
        notes.append(
            "export function run() {\n"
            "    // plugin logic\n"
            "}\n"
            "export const dependencies = ['pluginA'];"
        )

        # ============================================================
        # 16. C++ corrections
        # ============================================================
        if "#include <bits/stdc++.h>" in code:
            notes.append("C++ Correction: Avoid <bits/stdc++.h>. Include only the headers you actually need.")

        if "using namespace std;" in code:
            notes.append("C++ Correction: Avoid 'using namespace std;'. Use explicit std:: prefixes.")

        if "malloc(" in code and "new " in code:
            notes.append("C++ Correction: Do not mix malloc/free with new/delete.")

        notes.append("Canonical Plugin Pattern (C++):")
        notes.append(
            "class Plugin {\n"
            "public:\n"
            "    void run();\n"
            "    std::vector<std::string> dependencies;\n"
            "};"
        )

        # ============================================================
        # 17. Rust corrections
        # ============================================================
        if "unwrap()" in code and "expect(" not in code:
            notes.append("Rust Correction: Prefer expect() over unwrap() for clearer error messages.")

        if "mut " in code and "=" not in code:
            notes.append("Rust Correction: Avoid unnecessary mut bindings.")

        notes.append("Canonical Plugin Pattern (Rust):")
        notes.append(
            "pub struct Plugin {\n"
            "    pub fn run(&self) {}\n"
            "    pub dependencies: Vec<String>,\n"
            "}"
        )

        # ============================================================
        # 18. Go corrections
        # ============================================================
        if "panic(" in code:
            notes.append("Go Correction: Avoid panic() in normal plugin execution paths.")

        if "fmt.Println" in code and "log." not in code:
            notes.append("Go Correction: Prefer the 'log' package for structured logging in production code.")

        notes.append("Canonical Plugin Pattern (Go):")
        notes.append(
            "type Plugin struct {\n"
            "    Run         func()\n"
            "    Dependencies []string\n"
            "}"
        )

        # ============================================================
        # 19. Universal dependency execution reminder
        # ============================================================
        notes.append("Universal Reminder: Any dependency‑ordered execution should use DFS + cycle detection, not naive sorting or ad‑hoc heuristics.")

        return notes
