from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import math
import re


# ============================================================
# 3D STRUCTURE
# ============================================================

@dataclass
class Matrix3D:
    """
    3D structural view of a matrix operation.

    axis_x: raw text or high-level description
    axis_y: row-wise structure
    axis_z: operation metadata (op, dims, det, errors, etc.)
    """
    raw_text: str
    axis_x: str
    axis_y: List[List[float]]
    axis_z: Dict[str, Any]


# ============================================================
# CORE MATRIX TYPE
# ============================================================

@dataclass
class Matrix:
    data: List[List[float]]

    # -----------------------------
    # Basic properties
    # -----------------------------
    @property
    def rows(self) -> int:
        return len(self.data)

    @property
    def cols(self) -> int:
        return len(self.data[0]) if self.data else 0

    # -----------------------------
    # Pretty print
    # -----------------------------
    def __str__(self):
        return "[" + ", ".join(str(row) for row in self.data) + "]"

    # -----------------------------
    # Internal 3D builder
    # -----------------------------
    def _build_3d(self, op: str, result: Any = None, extra: Dict[str, Any] | None = None) -> Matrix3D:
        axis_z: Dict[str, Any] = {
            "op": op,
            "rows": self.rows,
            "cols": self.cols,
            "result": str(result) if result is not None else None,
        }
        if extra:
            axis_z.update(extra)
        return Matrix3D(
            raw_text=str(self),
            axis_x=str(self),
            axis_y=self.data,
            axis_z=axis_z,
        )

    # -----------------------------
    # Matrix addition
    # -----------------------------
    def __add__(self, other: "Matrix") -> "Matrix":
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Matrix dimensions must match for addition")
        result = Matrix([
            [self.data[i][j] + other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])
        self._last_3d = self._build_3d("add", result=result)
        return result

    # -----------------------------
    # Matrix subtraction
    # -----------------------------
    def __sub__(self, other: "Matrix") -> "Matrix":
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Matrix dimensions must match for subtraction")
        result = Matrix([
            [self.data[i][j] - other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])
        self._last_3d = self._build_3d("sub", result=result)
        return result

    # -----------------------------
    # Matrix multiplication
    # -----------------------------
    def __matmul__(self, other: "Matrix") -> "Matrix":
        if self.cols != other.rows:
            raise ValueError("Matrix dimensions incompatible for multiplication")
        result_data = []
        for i in range(self.rows):
            row = []
            for j in range(other.cols):
                s = 0
                for k in range(self.cols):
                    s += self.data[i][k] * other.data[k][j]
                row.append(s)
            result_data.append(row)
        result = Matrix(result_data)
        self._last_3d = self._build_3d(
            "matmul",
            result=result,
            extra={"other_rows": other.rows, "other_cols": other.cols},
        )
        return result

    # -----------------------------
    # Transpose
    # -----------------------------
    def T(self) -> "Matrix":
        result = Matrix([[self.data[j][i] for j in range(self.rows)] for i in range(self.cols)])
        self._last_3d = self._build_3d("transpose", result=result)
        return result

    # -----------------------------
    # Determinant (2×2, 3×3)
    # -----------------------------
    def det(self) -> float:
        if self.rows != self.cols:
            raise ValueError("Determinant requires a square matrix")

        if self.rows == 1:
            det_val = self.data[0][0]
        elif self.rows == 2:
            a, b = self.data[0]
            c, d = self.data[1]
            det_val = a * d - b * c
        elif self.rows == 3:
            a, b, c = self.data[0]
            d, e, f = self.data[1]
            g, h, i = self.data[2]
            det_val = (
                a * (e * i - f * h)
                - b * (d * i - f * g)
                + c * (d * h - e * g)
            )
        else:
            raise ValueError("Determinant only implemented for 1×1, 2×2, 3×3")

        self._last_3d = self._build_3d("det", result=det_val)
        return det_val

    # -----------------------------
    # Inverse (2×2, 3×3)
    # -----------------------------
    def inv(self) -> "Matrix":
        det_val = self.det()
        if abs(det_val) < 1e-12:
            raise ValueError("Matrix is singular")

        if self.rows == 2:
            a, b = self.data[0]
            c, d = self.data[1]
            result = Matrix([
                [ d/det_val, -b/det_val],
                [-c/det_val,  a/det_val]
            ])
            self._last_3d = self._build_3d("inv", result=result)
            return result

        if self.rows == 3:
            m = self.data
            a, b, c = m[0]
            d, e, f = m[1]
            g, h, i = m[2]

            adj = [
                [(e*i - f*h), -(b*i - c*h),  (b*f - c*e)],
                [-(d*i - f*g), (a*i - c*g), -(a*f - c*d)],
                [(d*h - e*g), -(a*h - b*g),  (a*e - b*d)]
            ]

            result = Matrix([[adj[r][c] / det_val for c in range(3)] for r in range(3)])
            self._last_3d = self._build_3d("inv", result=result)
            return result

        raise ValueError("Inverse only implemented for 2×2 and 3×3")


# ============================================================
# PARSER
# ============================================================

def parse_matrix(text: str) -> Matrix:
    """
    Parses a matrix from text like:
      [[1,2],[3,4]]
    """
    cleaned = text.replace(" ", "")
    # Robust row extraction: things inside [...]
    rows_raw = re.findall(r"

\[([0-9.,\-]+)\]

", cleaned)
    if not rows_raw:
        raise ValueError("Invalid matrix format")

    rows: List[List[float]] = []
    for row in rows_raw:
        parts = row.split(",")
        rows.append([float(x) for x in parts])

    M = Matrix(rows)
    # Attach 3D structure for parsing
    M._last_3d = Matrix3D(
        raw_text=text,
        axis_x=text,
        axis_y=M.data,
        axis_z={
            "op": "parse",
            "rows": M.rows,
            "cols": M.cols,
        },
    )
    return M
