#!/usr/bin/env python3
"""Detecta la posicion vertical (porcentaje) del composer de Qwen Studio en una captura.

El composer es una caja redondeada con borde claro: sus dos lineas horizontales
producen filas con ~300 pixeles en el rango de luminancia [48,80]. Esas dos filas
estan separadas por ~50-60 px. El centro entre ambas es el Y del composer.

Uso: qwen-composer-y.py <captura.png>   -> imprime el porcentaje (entero)
     Sale con 3 si no detecta; imprime 47 como respaldo.
"""
import sys
from PIL import Image


def detect(path: str) -> int | None:
    im = Image.open(path).convert("L")
    w, h = im.size
    x0, x1 = int(w * 0.28), int(w * 0.95)
    counts: dict[int, int] = {}
    for y in range(80, h):
        row = im.crop((x0, y, x1, y + 1)).tobytes()
        counts[y] = sum(1 for v in row[::2] if 48 <= v <= 80)
    cand = sorted(y for y, n in counts.items() if n >= 200)
    if not cand:
        return None
    bands: list[list[int]] = []
    for y in cand:
        if bands and y - bands[-1][-1] <= 2:
            bands[-1].append(y)
        else:
            bands.append([y])
    reps = [(max(counts[y] for y in b), sum(b) // len(b)) for b in bands]
    best = None
    for i in range(len(reps)):
        for j in range(i + 1, len(reps)):
            d = abs(reps[j][1] - reps[i][1])
            if 40 <= d <= 80:
                score = reps[i][0] + reps[j][0]
                if best is None or score > best[0]:
                    best = (score, reps[i][1], reps[j][1])
    if best is None:
        top = max(reps)[1]
        return round(top / h * 100)
    return round((best[1] + best[2]) / 2 / h * 100)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("uso: qwen-composer-y.py <captura.png>", file=sys.stderr)
        sys.exit(2)
    pct = detect(sys.argv[1])
    if pct is None:
        print(47)
        sys.exit(3)
    print(pct)
