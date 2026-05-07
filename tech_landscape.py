"""
US Grid-scale energy storage status and policy analysis

@author: Yining Wang
"""

# This script plots ES technology, by response time, duration, and 2023 maturity.


import matplotlib.pyplot as plt
from matplotlib.colors import Normalize, LinearSegmentedColormap
from matplotlib.cm import ScalarMappable
import numpy as np
import pandas as pd

plt.rcParams["figure.dpi"] = 300

df = pd.read_csv("Data/tech_landscape_manual.csv")

short_labels = {
    "Electro-chemical capacitor":     "Capacitor",
    "Flywheel":                       "Flywheel",
    "Lithium-ion battery":            "Lithium-ion",
    "Nickel-based battery":           "Ni-based",
    "Lead-acid battery":              "Lead-acid",
    "Sodium-based battery":           "Na-based",
    "Flow battery":                   "Flow battery",
    "Compressed air energy storage":  "CAES",
    "Pumped hydro storage":           "Pumped Hydro",
    "Sensible heat - Solids":         "Solid Heat",
    "Sensible heat - Liquid salt":    "Liquid salt Heat",
    "Latent heat - Low temperature":  "Low-T Latent heat",
    "Latent heat - High temperature": "High-T Latent heat",
    "Thermochemical - Sorption":      "Sorption reaction",
    "Thermochemical - Chemical reaction": "Chemical reaction",
}

# Adjusted response times to spread crowded clusters
response_adjusted = {
    "Electro-chemical capacitor":        0.05,
    "Flywheel":                          0.1,
    "Nickel-based battery":              0.4,
    "Lead-acid battery":                 0.5,
    "Lithium-ion battery":               1,
    "Sodium-based battery":              2,
    "Flow battery":                      5,
    "Pumped hydro storage":              80,
    "Latent heat - High temperature":    150,
    "Latent heat - Low temperature":     300,
    "Sensible heat - Solids":            400,
    "Compressed air energy storage":     900,
    "Thermochemical - Chemical reaction":700,
    "Sensible heat - Liquid salt":       1200,
    "Thermochemical - Sorption":         3600,
}

df["Response_hr"] = df["Technology"].map(response_adjusted) / 3600

cmap = LinearSegmentedColormap.from_list(
    "trl", ["#d73027", "#fc8d59", "#fee090", "#91bfdb", "#4575b4"], N=6
)
norm = Normalize(vmin=4, vmax=9)

def mw_to_size(mw):
    return (np.log10(np.maximum(mw, 0.001)) + 3) ** 2 * 22

fig, ax = plt.subplots(figsize=(15, 8))

# Service regions
service_regions = [
    (2e-4, 0.5,  "#FFA500", "Reserve & Response\nServices",    "#A05000"),
    (0.5,  10,   "#4472C4", "Transmission & Distribution\nSupport Grid",     "#2E5FA3"),
    (10,   200,  "#70AD47", "Bulk Power\nManagement", "#4E7A33"),
]
for x0, x1, bg, label, tc in service_regions:
    ax.axvspan(x0, x1, alpha=0.10, color=bg, zorder=0)
    x_label = 0.2 if x0 < 0.001 else np.sqrt(x0 * x1)
    ax.text(x_label, 0.96, label,
            transform=ax.get_xaxis_transform(),
            ha='center', va='top', fontsize=10, color=tc, fontweight='medium')

for x in [0.5, 10]:
    ax.axvline(x, color='gray', lw=0.8, ls='--', alpha=0.5, zorder=1)

for _, row in df.iterrows():
    tech = row['Technology']
    color = cmap(norm(row['TRL']))
    dur_min = max(row['Duration_min_hr'], 2e-4)
    dur_max = row['Duration_max_display_hr']
    response = row['Response_hr']
    mw = row['Representative_Power_MW']
    extends = row['Extends_beyond']
    label = short_labels.get(tech, tech)

    dur_center = np.sqrt(dur_min * dur_max)

    # Duration line
    ax.plot([dur_min, dur_max], [response, response],
            color=color, lw=2.5, alpha=0.75, zorder=2, solid_capstyle='round')

    # Arrow if extends beyond display
    if extends:
        ax.annotate('', xy=(dur_max * 1.6, response), xytext=(dur_max, response),
                    arrowprops=dict(arrowstyle='->', color=color, lw=1.5), zorder=3)

    # Bubble
    ax.scatter(dur_center, response, s=mw_to_size(mw),
               color=color, edgecolors='white', linewidths=0.8, zorder=4, alpha=0.92)

    x_text = 30 if tech == "Electro-chemical capacitor" else 0
    y_text = -5 if tech == "Thermochemical - Chemical reaction" else -10
    va_text = 'bottom' if tech == "Electro-chemical capacitor" else 'top'

    # Label below bubble
    ax.annotate(label, xy=(dur_center, response),
                xytext=(x_text, y_text), textcoords='offset points',
                ha='center', va=va_text, fontsize=10, zorder=5, color='#1a1a1a')

# Axes
ax.set_xscale('symlog', linthresh=0.5, linscale = 0.8)
ax.set_yscale('log')
ax.set_xlim(0, 100)
ax.set_ylim(1/360000, 8)

ax.set_xticks([1/60, 1, 10, 100])
ax.set_xticklabels(["1 min", "1 hr", "10 hr", "100+ hr"])
ax.set_xlabel("Discharge Duration", fontsize=11)

ytick_hr  = [1/360000, 1/3600, 1/60, 5/60, 1]
ytick_lbl = ["10 ms", "1 s", "1 min", "5 min", "1 hr"]
ax.set_yticks(ytick_hr)
ax.set_yticklabels(ytick_lbl)
ax.set_ylabel("Response Time", fontsize=11)

# Colorbar
sm = ScalarMappable(cmap=cmap, norm=norm)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, shrink=0.6, aspect=18, pad=0.02)
cbar.set_label("IEA Technology\nReadiness Level (TRL)", fontsize=9)
cbar.set_ticks([4, 5, 6, 7, 8, 9])

# Bubble size legend
legend_mw = [0.1, 1, 10, 100]
legend_handles = [
    plt.scatter([], [], s=mw_to_size(mw), color='gray', alpha=0.7,
                edgecolors='white', linewidths=0.8, label=f"{mw} MW")
    for mw in legend_mw
]
ax.legend(handles=legend_handles, title="Typical\nPower (MW)",
          loc='lower right', fontsize=9, title_fontsize=8,
          framealpha=0.85, handletextpad=1.2, borderpad=1)

ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

fig.tight_layout()
fig.savefig("Tech_landscape.png", dpi=300, bbox_inches='tight')
