"""Bitcoin-themed banner: binary 0/1 field with a bright ₿-shaped silhouette (reference-style)."""

from __future__ import annotations

# Inner bitmap: '#' = logo, '.' = hole/background inside the figure. Same width per row.
_INNER_W = 21
_LOGO_INNER = [
    ".....###########.....",
    "....##.........##....",
    "...##...........##...",
    "...##....###....##...",
    "...##...##.##...##...",
    "...##....###....##...",
    "...##...##.##...##...",
    "...##....###....##...",
    "...##...........##...",
    "....##.........##....",
    ".....###########.....",
]

W = 43


def _center(inner: str) -> str:
    if len(inner) != _INNER_W:
        msg = f"inner row length {len(inner)}, expected {_INNER_W}"
        raise ValueError(msg)
    pad = W - _INNER_W
    left = pad // 2
    right = pad - left
    return "." * left + inner + "." * right


LOGO_MASK = [
    "." * W,
    "." * W,
    *[_center(row) for row in _LOGO_INNER],
    "." * W,
    "." * W,
]


def mask_rows() -> list[str]:
    rows = list(LOGO_MASK)
    for i, r in enumerate(rows):
        if len(r) != W:
            msg = f"ascii_art row {i} length {len(r)}, expected {W}"
            raise ValueError(msg)
    return rows
