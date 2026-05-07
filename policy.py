"""
US Grid-scale energy storage status and policy analysis

@author: Yining Wang
"""

# This script visualizes state-level energy storage policies.

import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

plt.rcParams["figure.dpi"] = 300

states = gpd.read_file("Data/tl_2024_us_state.zip").to_crs("EPSG:5070")
policy = pd.read_csv("Data/policy.csv")

conus = states[~states["STUSPS"].isin(["AK", "HI", "PR", "GU", "VI", "MP", "AS"])]
conus = conus.merge(policy, left_on="STUSPS", right_on="State", how="left")

conus["any_policy"] = conus[["Procurement target (MW)", "Regulatory requirements", 
                               "Demonstration programs", "Financial incentives", 
                               "Consumer protection measures"]].notna().any(axis=1).astype(float)

#%% Plot state policies on map. Tried stacked bars on map, doesn't work well for NJ or so.


# Color map
policy_cols = [
    ("Procurement target (MW)","#d73027", "Procurement Target"),
    ("Regulatory requirements", "#fc8d59", "Regulatory Requirements"),
    ("Demonstration programs", "#fee090", "Demonstration Programs"),
    ("Financial incentives","#91bfdb", "Financial Incentives"),
    ("Consumer protection measures", "#4575b4", "Consumer Protection"),
    ("any_policy", "#70AD47", "Any Energy storage policy")
]

fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()
 
for i, (col, color, label) in enumerate(policy_cols):
    ax = axes[i]
 
    conus["has_policy"] = conus[col].notna() & (conus[col] != 0)
 
    conus[~conus["has_policy"]].plot(ax=ax, color="whitesmoke", edgecolor="gray", linewidth=0.4)
    conus[conus["has_policy"]].plot(ax=ax, color=color, edgecolor="gray", linewidth=0.4, alpha=0.85)
 
    ax.set_title(label, fontsize=20, fontweight='medium', pad=6)
    ax.set_axis_off()
 

fig.suptitle("State Energy Storage Policies", fontsize=25, y=1.01)
plt.tight_layout()
plt.savefig("Policy_map.png", bbox_inches="tight")
plt.show()

#%% Check how state policies distribute across market types

policy_cols_data = [
    "Procurement target (MW)",
    "Regulatory requirements", 
    "Demonstration programs",
    "Financial incentives",
    "Consumer protection measures"
]

policy["has_target"] = policy["Procurement target (MW)"].notna().astype(int)
policy["regulated_label"] = policy["Regulated"].map({1.0: "Regulated", 0.0: "Restructured"}).fillna("Restructured")

summary = policy.groupby("regulated_label")[policy_cols_data].apply(
    lambda x: x.notna().sum()
).T

print(summary)
print()
print("Total states:", policy["regulated_label"].value_counts())