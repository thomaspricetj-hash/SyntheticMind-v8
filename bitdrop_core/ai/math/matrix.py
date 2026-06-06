from __future__ import annotations
from dataclasses import dataclass
from typing import List
import math
import re


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
    # Matrix addition
    # -----------------------------
    def __add__(self, other: "Matrix") -> "Matrix":
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Matrix dimensions must match for addition")
        return Matrix([
            [self.data[i][j] + other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    # -----------------------------
    # Matrix subtraction
    # -----------------------------
    def __sub__(self, other: "Matrix") -> "Matrix":
        if self.rows != other.rows or self.cols != other.cols:
            raise ValueError("Matrix dimensions must match for subtraction")
        return Matrix([
            [self.data[i][j] - other.data[i][j] for j in range(self.cols)]
            for i in range(self.rows)
        ])

    # -----------------------------
    # Matrix multiplication
    # -----------------------------
    def __matmul__(self, other: "Matrix") -> "Matrix":
        if self.cols != other.rows:
            raise ValueError("Matrix dimensions incompatible for multiplication")
        result = []
        for i in range(self.rows):
            row = []
            for j in range(other.cols):
                s = 0
                for k in range(self.cols):
                    s += self.data[i][k] * other.data[k][j]
                row.append(s)
            result.append(row)
        return Matrix(result)

    # -----------------------------
    # Transpose
    # -----------------------------
    def T(self) -> "Matrix":
        return Matrix([[self.data[j][i] for j in range(self.rows)] for i in range(self.cols)])

    # -----------------------------
    # Determinant (2×2, 3×3)
    # -----------------------------
    def det(self) -> float:
        if self.rows != self.cols:
            raise ValueError("Determinant requires a square matrix")

        if self.rows == 1:
            return self.data[0][0]

        if self.rows == 2:
            a, b = self.data[0]
            c, d = self.data[1]
            return a * d - b * c

        if self.rows == 3:
            a, b, c = self.data[0]
            d, e, f = self.data[1]
            g, h, i = self.data[2]
            return (
                a * (e * i - f * h)
                - b * (d * i - f * g)
                + c * (d * h - e * g)
            )

        raise ValueError("Determinant only implemented for 1×1, 2×2, 3×3")

    # -----------------------------
    # Inverse (2×2, 3×3)
    # -----------------------------
    def inv(self) -> "Matrix":
        det = self.det()
        if abs(det) < 1e-12:
            raise ValueError("Matrix is singular")

        if self.rows == 2:
            a, b = self.data[0]
            c, d = self.data[1]
            return Matrix([
                [ d/det, -b/det],
                [-c/det,  a/det]
            ])

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

            return Matrix([[adj[r][c] / det for c in range(3)] for r in range(3)])

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
    m = re.findall(r"

\[([0-9.,\-]+)\]

", cleaned)
    if not m:
        raise ValueError("Invalid matrix format")

    rows = []
    for row in m:
        parts = row.split(",")
        rows.append([float(x) for x in parts])

    return Matrix(rows)
