"""
Plotters for battle datasets.
Currently provides PlotLanchester: casualties of winning side vs N for each unit type.
"""
from collections import defaultdict
from pathlib import Path
from typing import List, Dict, Any, Optional


def plot_lanchester(dataset: List[Dict[str, Any]], graph_path: str) -> Optional[str]:
    """
    dataset: list of rows with keys: unit_type, N, casualties_winner
    Produces a PNG with one curve per unit_type, x=N, y=casualties_winner.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; skipping graph generation.")
        return None

    series = defaultdict(list)
    for row in dataset:
        series[row["unit_type"]].append((row["N"], row["casualties_winner"]))

    plt.figure(figsize=(8, 5))
    for unit_type, points in series.items():
        pts = sorted(points, key=lambda x: x[0])
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        plt.plot(xs, ys, marker="o", label=unit_type)

    plt.title("Lanchester casualties of winning side")
    plt.xlabel("N (base size, N vs 2N)")
    plt.ylabel("Casualties (winning side)")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()

    out_path = Path(graph_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_path, dpi=150)
    plt.close()
    return str(out_path.resolve())