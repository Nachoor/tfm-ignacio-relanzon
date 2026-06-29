from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


ROOT = Path(__file__).resolve().parents[3]

METRIC_LABELS = ["Precision", "Recall", "F1"]
SUBSETS = ["Manual", "Auto"]
METRICS = {
    "Manual": [0.698, 0.995, 0.820],
    "Auto": [0.552, 0.969, 0.703],
}

MEAN_LABELS = ["Manual", "Auto", "Sin auto"]
MEAN_EXPECTED = [12.87, 8.66, 0.00]
MEAN_DETECTED = [18.34, 15.19, 3.75]


def add_labels(ax, bars, fmt="{:.3f}", dy=0.02):
    for bar in bars:
        height = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + dy,
            fmt.format(height),
            ha="center",
            va="bottom",
            fontsize=8,
        )


def main() -> None:
    plt.rcParams.update({
        "font.family": "DejaVu Sans",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.22,
        "grid.linewidth": 0.7,
    })

    fig, axes = plt.subplots(1, 2, figsize=(11.2, 4.2), dpi=180)
    colors = ["#4C78A8", "#F58518", "#54A24B"]

    x = np.arange(len(SUBSETS))
    width = 0.22
    for i, label in enumerate(METRIC_LABELS):
        values = [METRICS[s][i] for s in SUBSETS]
        bars = axes[0].bar(x + (i - 1) * width, values, width, label=label, color=colors[i])
        add_labels(axes[0], bars)

    axes[0].set_title("Metricas micro por subconjunto", fontsize=11, pad=10)
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(SUBSETS)
    axes[0].set_ylim(0, 1.12)
    axes[0].set_ylabel("Valor")
    axes[0].legend(frameon=False, loc="upper center", ncols=3, bbox_to_anchor=(0.5, -0.12))

    x2 = np.arange(len(MEAN_LABELS))
    width2 = 0.34
    bars_exp = axes[1].bar(x2 - width2 / 2, MEAN_EXPECTED, width2, label="Esperadas", color="#4C78A8")
    bars_det = axes[1].bar(x2 + width2 / 2, MEAN_DETECTED, width2, label="Detectadas", color="#F58518")
    add_labels(axes[1], bars_exp, fmt="{:.2f}", dy=0.35)
    add_labels(axes[1], bars_det, fmt="{:.2f}", dy=0.35)
    axes[1].set_title("Media de skills por CV", fontsize=11, pad=10)
    axes[1].set_xticks(x2)
    axes[1].set_xticklabels(MEAN_LABELS)
    axes[1].set_ylim(0, 21)
    axes[1].set_ylabel("Skills por CV")
    axes[1].legend(frameon=False, loc="upper center", ncols=2, bbox_to_anchor=(0.5, -0.12))

    fig.tight_layout()

    for rel in ["docs/figures", "figures"]:
        out_dir = ROOT / rel
        out_dir.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_dir / "fig39_validacion_500cvs.png", bbox_inches="tight")
        fig.savefig(out_dir / "fig39_validacion_500cvs.pdf", bbox_inches="tight")


if __name__ == "__main__":
    main()
