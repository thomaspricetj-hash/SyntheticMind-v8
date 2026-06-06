from __future__ import annotations
from typing import List, Optional
import math
import re

# Local symbolic system
from .symbolic import Expr, Symbol, Eq, Number, Add, Mul, Pow, Neg
from .derivation import d
from .solver import solve_linear, solve_quadratic
from .detectors import looks_like_math
from .semantic_math import embed_math_text




# -------------------------------------------------------------------------
# FIXED extract_equation()
# -------------------------------------------------------------------------
def extract_equation(text: str) -> str:
    text = text.strip()
    return text


class MathEngine:
    """
    High-level math engine
    """

    def __init__(self, base_engine=None, user_id: str = "math"):
        if base_engine is None:
            base_engine = EchoEngine()

        init_memory(base_engine, user_id=user_id)
        self.ua = UniversalAI(base_engine)
        self.skimmer = self.ua.skimmer

    # -------------------------------------------------------------------------
    # TOKENIZER
    # -------------------------------------------------------------------------

    def _tokenize(self, text: str) -> List[str]:
        pattern = r"[A-Za-z]+|\d+\.\d+|\d+|[\+\-\*\^\(\)]"
        tokens = re.findall(pattern, text)
        tokens = self._insert_implicit_mul(tokens)
        return tokens

    def _insert_implicit_mul(self, tokens: List[str]) -> List[str]:
        out: List[str] = []
        for i, tok in enumerate(tokens):
            out.append(tok)

            if i < len(tokens) - 1:
                nxt = tokens[i + 1]

                is_num = tok.replace('.', '', 1).isdigit()
                is_next_num = nxt.replace('.', '', 1).isdigit()
                is_sym = tok.isalpha()
                is_next_sym = nxt.isalpha()

                if is_num and is_next_sym:
                    out.append("*")
                if is_sym and is_next_sym:
                    out.append("*")
                if tok == ")" and (is_next_sym or is_next_num):
                    out.append("*")
                if (is_sym or is_num) and nxt == "(":
                    out.append("*")

        return out

    # -------------------------------------------------------------------------
    # PARSER
    # -------------------------------------------------------------------------

    def parse_expr(self, text: str) -> Expr:
        tokens = self._tokenize(text)
        expr, pos = self._parse_add(tokens, 0)
        if pos != len(tokens):
            raise ValueError(f"Unexpected tokens at end: {tokens[pos:]}")
        return expr.simplify()

    def _parse_add(self, tokens, pos):
        node, pos = self._parse_mul(tokens, pos)
        while pos < len(tokens) and tokens[pos] in ("+", "-"):
            op = tokens[pos]
            rhs, pos = self._parse_mul(tokens, pos + 1)
            if op == "+":
                node = Add(node, rhs)
            else:
                node = Add(node, Neg(rhs))
        return node, pos

    def _parse_mul(self, tokens, pos):
        node, pos = self._parse_pow(tokens, pos)
        while pos < len(tokens) and tokens[pos] == "*":
            rhs, pos = self._parse_pow(tokens, pos + 1)
            node = Mul(node, rhs)
        return node, pos

    def _parse_pow(self, tokens, pos):
        node, pos = self._parse_atom(tokens, pos)
        while pos < len(tokens) and tokens[pos] == "^":
            rhs, pos = self._parse_atom(tokens, pos + 1)
            node = Pow(node, rhs)
        return node, pos

    def _parse_atom(self, tokens, pos):
        tok = tokens[pos]
        if tok == "(":
            node, pos = self._parse_add(tokens, pos + 1)
            if pos >= len(tokens) or tokens[pos] != ")":
                raise ValueError("Missing )")
            return node, pos + 1
        if tok.replace('.', '', 1).isdigit():
            return Number(float(tok)), pos + 1
        return Symbol(tok), pos + 1

    # -------------------------------------------------------------------------
    # CORE OPS
    # -------------------------------------------------------------------------

    def simplify(self, text: str) -> str:
        expr = self.parse_expr(text)
        simp = expr.simplify()
        memory.write(f"simplify: {text} -> {simp}", tags={"op": "simplify"})
        return str(simp)

    def derivative(self, text: str, var_name: str = "x") -> str:
        expr = self.parse_expr(text)
        var = Symbol(var_name)
        der = d(expr, var).simplify()
        memory.write(f"d/d{var_name} {text} = {der}", tags={"op": "derivative"})
        return str(der)

    # -------------------------------------------------------------------------
    # REUSE LOOP
    # -------------------------------------------------------------------------

    def _search_similar_problems(self, text: str, limit: int = 3):
        q_emb = embed_math_text(text)
        scored = []
        for item in memory.items:
            if item.tags.get("op") in ("solve", "derivative") and item.embedding:
                score = cosine(q_emb, item.embedding)
                if score > 0:
                    scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:limit]]

    # -------------------------------------------------------------------------
    # QUADRATIC FALLBACK
    # -------------------------------------------------------------------------

    def _try_quadratic_fallback(self, left: str, right: str, var_name: str = "x") -> Optional[str]:
        if right.strip() not in ("0", "0.0"):
            return None

        s = left.replace(" ", "")

        pattern = rf"^([+\-]?\d*){var_name}\^2([+\-]?\d*){var_name}([+\-]?\d+)$"
        m = re.match(pattern, s)
        if not m:
            return None

        a_str, b_str, c_str = m.groups()

        def parse_coeff(raw: str, default_one: bool = False) -> float:
            if raw in ("", "+") and default_one:
                return 1.0
            if raw == "-":
                return -1.0
            return float(raw)

        a = parse_coeff(a_str, default_one=True)
        b = parse_coeff(b_str, default_one=True)
        c = float(c_str)

        if a == 0:
            if b == 0:
                return None
            x = -c / b
            return f"{var_name} = {x}"

        disc = b * b - 4 * a * c
        if disc < 0:
            return f"No real solutions for {a}{var_name}^2 + {b}{var_name} + {c} = 0"

        sqrt_disc = math.sqrt(disc)
        x1 = (-b + sqrt_disc) / (2 * a)
        x2 = (-b - sqrt_disc) / (2 * a)

        if abs(x1 - x2) < 1e-12:
            return f"{var_name} = {x1}"
        return f"{var_name} = {x1}, {x2}"

    # -------------------------------------------------------------------------
    # SOLVER
    # -------------------------------------------------------------------------

    def solve(self, text: str, var_name: str = "x") -> str:
        if not looks_like_math(text):
            return self.ua.chat(text, tags={"op": "nlq"})

        similar = self._search_similar_problems(text)
        if similar:
            context = "\n".join(it.content for it in similar)
            skimmed = self.skimmer.skim(context)
            memory.write(
                f"reuse_context for: {text}\n{skimmed}",
                tags={"op": "reuse", "source": "math"}
            )

        eq_text = extract_equation(text)

        if "=" not in eq_text:
            expr = self.parse_expr(eq_text)
            simp = expr.simplify()

            if isinstance(simp, Number):
                memory.write(f"eval: {eq_text} -> {simp.value}", tags={"op": "eval"})
                return str(simp.value)

            memory.write(f"simplify_expr: {eq_text} -> {simp}", tags={"op": "simplify_expr"})
            return str(simp)

        left, right = eq_text.split("=", 1)
        left = left.strip()
        right = right.strip()

        quad_fallback = self._try_quadratic_fallback(left, right, var_name=var_name)
        if quad_fallback is not None:
            memory.write(
                f"solve(quadratic_fallback): {eq_text} -> {quad_fallback}",
                tags={"op": "solve", "kind": "quadratic_fallback"}
            )
            return quad_fallback

        try:
            eq = Eq(self.parse_expr(left), self.parse_expr(right))
        except Exception as e:
            msg = f"Parse error for equation: {left} = {right} ({e})"
            memory.write(msg, tags={"op": "solve", "status": "parse_fail"})
            return msg

        var = Symbol(var_name)

        lin = solve_linear(eq, var)
        if lin is not None:
            result = f"{var_name} = {lin}"
            memory.write(f"solve(linear): {eq_text} -> {result}", tags={"op": "solve", "kind": "linear"})
            return result

        quad = solve_quadratic(eq, var)
        if quad is not None:
            if not quad:
                msg = f"No real solutions for {eq}"
                memory.write(msg, tags={"op": "solve", "kind": "quadratic", "status": "no_real"})
                return msg
            if len(quad) == 1:
                result = f"{var_name} = {quad[0]}"
            else:
                result = f"{var_name} = {quad[0]}, {quad[1]}"
            memory.write(f"solve(quadratic): {eq_text} -> {result}", tags={"op": "solve", "kind": "quadratic"})
            return result

        msg = f"Cannot solve equation (unsupported form): {eq}"
        memory.write(msg, tags={"op": "solve", "status": "fail"})
        return msg

    # -------------------------------------------------------------------------
    # ENTRYPOINT
    # -------------------------------------------------------------------------

    def analyze(self, text: str) -> str:
        if looks_like_math(text):
            emb = embed_math_text(text)
            memory.write("math_query", tags={"type": "math"}, agent="detector", embedding=emb)
            return self.solve(text)
        else:
            return self.ua.chat(text, tags={"type": "nlq"})

    # -------------------------------------------------------------------------
    # CAS EXTENSIONS (HOOKS)
    # -------------------------------------------------------------------------

    def integrate_expr(self, text: str, var_name: str = "x") -> str:
        from .symbolic_cas import integrate
        expr = self.parse_expr(text)
        var = Symbol(var_name)
        res = integrate(expr, var)
        return str(res) if res else "Cannot integrate expression"

    def limit_expr(self, expr_str: str, var_name: str, point: float) -> str:
        from .symbolic_cas import limit
        res = limit(expr_str, var_name, point)
        return res.description

    def factor_expr(self, text: str, var_name: str = "x") -> str:
        from .symbolic_cas import factor_quadratic
        expr = self.parse_expr(text)
        var = Symbol(var_name)
        res = factor_quadratic(expr, var)
        return str(res) if res else "Cannot factor expression"

    # -------------------------------------------------------------------------
    # MATRIX ENGINE HOOKS
    # -------------------------------------------------------------------------

    def matrix_parse(self, text: str):
        from .matrix import parse_matrix
        return parse_matrix(text)

    def matrix_det(self, text: str) -> str:
        from .matrix import parse_matrix
        M = parse_matrix(text)
        return str(M.det())

    def matrix_inv(self, text: str) -> str:
        from .matrix import parse_matrix
        M = parse_matrix(text)
        return str(M.inv())

    def matrix_mul(self, A: str, B: str) -> str:
        from .matrix import parse_matrix
        M1 = parse_matrix(A)
        M2 = parse_matrix(B)
        return str(M1 @ M2)

    def matrix_add(self, A: str, B: str) -> str:
        from .matrix import parse_matrix
        M1 = parse_matrix(A)
        M2 = parse_matrix(B)
        return str(M1 + M2)

    def matrix_sub(self, A: str, B: str) -> str:
        from .matrix import parse_matrix
        M1 = parse_matrix(A)
        M2 = parse_matrix(B)
        return str(M1 - M2)








