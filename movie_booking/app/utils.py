from typing import List, Set
import string

def seat_codes(rows: int, cols: int) -> List[str]:
    letters = list(string.ascii_uppercase[:rows])  # 1->A, 2->B, ...
    return [f"{r}{c}" for r in letters for c in range(1, cols + 1)]

def code_from_row_col(row: int, col: int) -> str:
    letter = string.ascii_uppercase[row - 1]
    return f"{letter}{col}"

def seat_type_for(code: str, vip: Set[str], disabled: Set[str]) -> str:
    if code in disabled:
        return "blocked"
    if code in vip:
        return "vip"
    return "standard"

def apply_promo(total: float, code: str | None) -> float:
    if not code:
        return 0.0
    c = code.upper()
    if c == "DISCOUNT10":
        return 0.10 * total
    if c == "STUDENT20":
        return 0.20 * total
    return 0.0