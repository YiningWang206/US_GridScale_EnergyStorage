"""
US Grid-scale energy storage status and policy analysis

@author: Yining Wang
"""

# This script maps energy storage data from GESDB and analyzes spatial distribution.

import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["figure.dpi"] = 300

gesdb = pd.read_csv("Data/GESDB/GESDB_Project_Data_full.csv")

gesdb_us = gesdb[gesdb["Country"] == "United States"].copy()
print(f"US projects: {len(gesdb_us)}")
print(gesdb_us["Status"].value_counts())

gesdb_op = gesdb_us[gesdb_us["Status"] == "Operational"].copy()
print(f"Operational projects: {len(gesdb_op)}")
print(gesdb_op["Subsystems.0.Storage Device.Technology Broad Category"].value_counts())

print(gesdb_op["Discharge Duration at Rated Power (hrs)"].describe())
print(gesdb_op["Discharge Duration at Rated Power (hrs)"].isna().sum())

gesdb_op["Discharge Duration at Rated Power (hrs)"] = gesdb_op[
    "Discharge Duration at Rated Power (hrs)"].replace(0, pd.NA)





#%% Plot duration of installed ES, across tech type

import seaborn as sns

tech_order_dur = gesdb_op.groupby(
    "Subsystems.0.Storage Device.Technology Mid-Type"
)["Discharge Duration at Rated Power (hrs)"].median().sort_values(ascending=True).index

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))

# left, duration histogram
gesdb_op[gesdb_op["Discharge Duration at Rated Power (hrs)"] <= 24][
    "Discharge Duration at Rated Power (hrs)"].hist(bins=30, ax=ax1, color="steelblue")
ax1.set_xlabel("Discharge Duration (hrs)",fontsize=14)
ax1.set_ylabel("Count",fontsize=14)
ax1.set_title("Distribution of Discharge Duration (≤24 hrs)",fontsize=16)
ax1.axvline(x=4, color='orange', linestyle='--', label="4-hr threshold")
ax1.axvline(x=10, color='red', linestyle='--', label="10-hr threshold (LDES)")
ax1.legend(fontsize=14)

# Right：strip plot
sns.stripplot(data=gesdb_op[gesdb_op["Discharge Duration at Rated Power (hrs)"] <= 50],
              x="Discharge Duration at Rated Power (hrs)",
              y="Subsystems.0.Storage Device.Technology Mid-Type",
              order=tech_order_dur,
              alpha=0.5, jitter=True, ax=ax2, color="steelblue", size=4)

for i, tech in enumerate(tech_order_dur):
    med = gesdb_op[gesdb_op["Subsystems.0.Storage Device.Technology Mid-Type"] == tech][
        "Discharge Duration at Rated Power (hrs)"].median()
    ax2.scatter(med, i, color="red", s=30, zorder=5, marker="D")

ax2.axvline(x=4, color='orange', linestyle='--', label="4-hr threshold")
ax2.axvline(x=10, color='red', linestyle='--', label="10-hr threshold (LDES)")
ax2.scatter([], [], color="red", marker="D", s=30, label="Median")
ax2.set_xlabel("Discharge Duration (hrs)",fontsize=14)
ax2.set_ylabel("",fontsize=14)
ax2.tick_params(axis='y', labelsize=12)
ax2.set_title("Duration Distribution by Technology",fontsize=16)
ax2.legend(fontsize=14)

plt.tight_layout()

fig.savefig("GESDB_Duration.png")

#%% Read state boundary and transmission line shapefiles.

import geopandas as gpd

states = gpd.read_file("Data/tl_2024_us_state.zip")
print(states.crs)
print(states.columns.tolist())

'''
transmission = gpd.read_file("US_Electric_Power_Transmission_Lines_1178057934560076066.gpkg")
print(transmission.crs)
print(transmission.columns.tolist())
'''

#%% Set coordinates.

states = states.to_crs("EPSG:4326")

#transmission = transmission.to_crs("EPSG:4326")

#print(transmission["VOLT_CLASS"].value_counts())

#high_voltage = transmission[transmission["VOLT_CLASS"].isin(["345", "500", "735 AND ABOVE"])]
#print(f"High voltage lines: {len(high_voltage)}")

gesdb_geo = gpd.GeoDataFrame(
    gesdb_op,
    geometry=gpd.points_from_xy(gesdb_op["Longitude"], gesdb_op["Latitude"]),
    crs="EPSG:4326"
)

gesdb_geo = gesdb_geo.dropna(subset=["Latitude", "Longitude"])
print(f"Projects with coordinates: {len(gesdb_geo)}")

#%% Plot installation points.
## (I'm not using this anymore; Can't simply map storage demand to transmission)

gesdb_color_map = {
    "Lithium-ion battery": "#4C72B0",
    "Flywheel": "#DD8452",
    "Sensible heat": "#55A868",
    "Compressed air energy storage": "#C44E52",
    "Nickel-based battery": "#8172B3",
    "Lead-acid battery": "#937860",
    "Flow battery": "#DA8BC3",
    "Sodium-based battery": "#8C8C8C",
    "Latent heat": "#CCB974",
    "Heat thermal storage": "#64B5CD",
    "Electro-chemical capacitor": "#1D1D1D",
    "Pumped hydro storage": "#2CA02C",
}

# Some of the states are too off...

states_conus = states[~states["STUSPS"].isin(["AK", "HI", "PR", "GU", "VI", "MP", "AS"])]
gesdb_conus = gesdb_geo[~gesdb_geo["State/Province"].isin(["AK", "HI", "PR", "GU", "VI", "MP", "AS"])]
gesdb_conus = gesdb_geo[
    (gesdb_geo["Longitude"] >= -130) & 
    (gesdb_geo["Longitude"] <= -60) &
    (gesdb_geo["Latitude"] >= 24) & 
    (gesdb_geo["Latitude"] <= 50)
].copy()

'''
gesdb_conus["color"] = gesdb_conus["Subsystems.0.Storage Device.Technology Mid-Type"].map(gesdb_color_map)
gesdb_conus["duration_plot"] = gesdb_conus["Discharge Duration at Rated Power (hrs)"].clip(upper=50).fillna(2)
gesdb_conus["markersize"] = gesdb_conus["duration_plot"] * 3 + 5  

print(f"CONUS projects: {len(gesdb_conus)}")
transmission_conus = high_voltage.clip(states_conus.union_all())

fig, ax = plt.subplots(figsize=(16, 10))

states_conus.plot(ax=ax, color="whitesmoke", edgecolor="gray", linewidth=0.5)

transmission_conus.plot(ax=ax, color="lightblue", linewidth=1, alpha=1, label="Transmission Lines (≥345kV)", zorder = 1)

for tech, group in gesdb_conus.groupby("Subsystems.0.Storage Device.Technology Mid-Type"):
    group.plot(ax=ax, zorder=2, color=gesdb_color_map.get(tech, "gray"),
               markersize=group["markersize"],
               alpha=0.7, label=tech)

ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=14, markerscale=2)

ax.set_title("US Grid-Scale Energy Storage Projects and High-Voltage Transmission Lines", fontsize=16)
ax.set_axis_off()
plt.tight_layout()

fig.savefig("Installation_map.png")

'''

#%%  # Just to check if ISO matters.

rto_stats = gesdb_conus.groupby("ISO/RTO").agg(
    n_projects=("ID", "count"),
    total_capacity_mwh=("Storage Capacity (kWh)", "sum")
).reset_index()

regulated_map = {
    "CAISO": 0,
    "PJM": 0,
    "MISO": 0,
    "NYISO": 0,
    "ISO-NE": 0,
    "ISONE": 0,
    "ERCOT": 0,
    "SPP": 0,
    "BANC": 1,
    "IID": 1,
}
rto_stats["regulated"] = rto_stats["ISO/RTO"].map(regulated_map).fillna(1)

rto_stats["total_capacity_mwh"] = rto_stats["total_capacity_mwh"] / 1000

rto_stats = rto_stats.sort_values("total_capacity_mwh", ascending=False)


fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
colors = rto_stats["regulated"].map({0: "steelblue", 1: "orange"})
rto_stats.plot(kind="bar", x="ISO/RTO", y="n_projects", ax=ax1, color=colors, legend=False)
ax1.set_xlabel("ISO/RTO")
ax1.set_ylabel("Number of Projects")
ax1.set_title("Energy Storage Projects by ISO/RTO")
ax1.tick_params(axis='x', rotation=45)

rto_stats.plot(kind="bar", x="ISO/RTO", y="total_capacity_mwh", ax=ax2, color=colors, legend=False)
ax2.set_xlabel("ISO/RTO")
ax2.set_ylabel("Total Storage Capacity (MWh)")
ax2.set_title("Energy Storage Capacity by ISO/RTO")
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()


#%% Plot gap between RE Capacity (MW) per Storage (GWh) 
## (I'm also not using this anymore; Not sure what info I can convey with this map)
## Also MW/GWh doesn't seem comparable.

panel = pd.read_csv("Data/renewable_panel.csv")

panel["re_capacity_mw"] = panel["wind_mw"] + panel["solar_mw"]

gap = panel[panel["year"] == 2024].copy()

gap["re_per_storage"] = gap["re_capacity_mw"] / (gap["energy_total"] / 1000 + 1)
gap = gap.sort_values("re_per_storage", ascending=False)
print(gap[["State", "re_capacity_mw", "energy_total", "re_per_storage"]].head(15))

gap_map = states_conus.merge(
    gap[["State", "re_per_storage"]], 
    left_on="STUSPS", right_on="State", 
    how="left"
)

'''

fig, ax = plt.subplots(figsize=(16, 10))

gap_map.plot(column="re_per_storage", ax=ax,
             cmap="RdYlGn_r",
             legend=True,
             legend_kwds={"label": "RE Capacity (MW) per Storage (GWh)",
                          "shrink": 0.5},
             missing_kwds={"color": "lightgray"})

states_conus.boundary.plot(ax=ax, color="gray", linewidth=0.5)

for _, row in gap_map.iterrows():
    if row.geometry is not None:
        ax.annotate(row["STUSPS"], 
                    xy=(row.geometry.centroid.x, row.geometry.centroid.y),
                    ha="center", va="center", fontsize=12, color="black")

ax.set_title("Renewable Energy vs Energy Storage Gap by State (2024)")
ax.set_axis_off()
plt.tight_layout()
plt.show()

fig.savefig("Gap_map.png")

'''

#%% Finally, check function

app_cols = [c for c in gesdb_op.columns if "Applications" in c]
print(app_cols)

for col in app_cols:
    count = gesdb_op[col].notna().sum()
    if count > 0:
        print(f"{col}: {count}")
        print(f"  Values: {gesdb_op[col].dropna().unique()[:5]}")
        
#%% Check projects by service type

all_apps = pd.Series(dtype=str)
for col in app_cols:
    all_apps = pd.concat([all_apps, gesdb_op[col].dropna()])

app_counts = all_apps.value_counts()
print(app_counts)

#%% Service heatmap

rows = []
for _, row in gesdb_op.iterrows():
    tech = row["Subsystems.0.Storage Device.Technology Mid-Type"]
    duration = row["Discharge Duration at Rated Power (hrs)"]
    for col in app_cols:
        if pd.notna(row[col]):
            rows.append({
                "service": row[col],
                "tech": tech,
                "duration": duration
            })

app_long = pd.DataFrame(rows)

# Mapping back to figure 1's three categories. I am using definition from GESDB.

service_category = {
    # Ancillary Services → Reserve & Response
    "Black Start":                           "Reserve & Response",
    "Frequency Regulation":                  "Reserve & Response",
    "Operating Reserve (Non-Spinning)":      "Reserve & Response",
    "Operating Reserve (Spinning)":          "Reserve & Response",
    "Operating Reserve (Supplementary)":     "Reserve & Response",
    "Ramp Support":                          "Reserve & Response",
    "Voltage Support":                       "Reserve & Response",
    "Stability Damping Control":             "Reserve & Response",
    # Bulk Energy Services → Bulk Power Management
    "Electric Energy Time Shift (Arbitrage)":"Bulk Power Management",
    "Renewable Energy Time Shift":           "Bulk Power Management",
    "Renewable Energy Time Shift (Firming)": "Bulk Power Management",
    "Electric Supply Capacity":              "Bulk Power Management",
    # Transmission & Distribution → T&D Load Shifting
    "Transmission Congestion Relief":        "T&D Load Shifting",
    "Transmission Upgrade Deferral":         "T&D Load Shifting",
    "Distribution Upgrade Deferral":         "T&D Load Shifting",
    "Reliability":                           "T&D Load Shifting",
    "Demand Charge Management":              "T&D Load Shifting",
    "Retail TOU Energy Charges":             "T&D Load Shifting",
    "Microgrid Applications":                "T&D Load Shifting",
    "Resilience (Back-up Power)":            "T&D Load Shifting",
    "Transportation Services":               "T&D Load Shifting",
}

category_colors = {
    "Reserve & Response": "#A05000",
    "Bulk Power Management": "#4E7A33",
    "T&D Load Shifting": "#2E5FA3",
}

# heatmap: tech vs service
category_order = {"Reserve & Response": 0, "T&D Load Shifting": 1, "Bulk Power Management": 2}

heatmap_data = app_long.groupby(["service", "tech"]).size().unstack(fill_value=0)
heatmap_data["category"] = heatmap_data.index.map(
    lambda x: service_category.get(x, "T&D Load Shifting")
)
heatmap_data["sort_key"] = heatmap_data["category"].map(category_order)
heatmap_data = heatmap_data.sort_values("sort_key").drop(columns=["category", "sort_key"])

fig, ax = plt.subplots(figsize=(14, 10))
sns.heatmap(heatmap_data, ax=ax, cmap="YlOrRd", 
            linewidths=0.5, annot=True, fmt="d",
            cbar_kws={"label": "Number of Projects"})
cbar = ax.collections[0].colorbar
cbar.set_label("Number of Projects", fontsize=14)
cbar.ax.tick_params(labelsize=10)
ax.set_xlabel("Technology", fontsize=14)
ax.set_ylabel("Service", fontsize=14)
ax.tick_params(axis='x', labelsize=12)
ax.tick_params(axis='y', labelsize=12)
for label in ax.get_yticklabels():
    service = label.get_text()
    cat = service_category.get(service, "T&D Load Shifting")
    label.set_color(category_colors[cat])
fig.tight_layout()

fig.savefig("Service_heatmap.png")

# Weird. Why so many latent heat projects?

print(gesdb_op[gesdb_op["Subsystems.0.Storage Device.Technology Mid-Type"] == "Latent heat"][
    ["Project/Plant Name", "State/Province", "Storage Capacity (kWh)", "Discharge Duration at Rated Power (hrs)"]
].sort_values("Storage Capacity (kWh)", ascending=False).head(20))

#%% Finally, overlay projects onto the policy map.

import matplotlib.patches as mpatches
from matplotlib.lines import Line2D
import numpy as np

policy = pd.read_csv("Data/policy.csv")

states_conus = states_conus.merge(policy, left_on="STUSPS", right_on="State", how="left")
states_conus["any_policy"] = states_conus[["Procurement target (MW)", "Regulatory requirements",
                               "Demonstration programs", "Financial incentives",
                               "Consumer protection measures"]].notna().any(axis=1)


fig, ax = plt.subplots(figsize=(18, 10))

states_conus[~states_conus["any_policy"]].plot(ax=ax, color="whitesmoke", edgecolor="gray", linewidth=0.5)
states_conus[states_conus["any_policy"]].plot(ax=ax, color="#70AD47", edgecolor="gray", linewidth=0.5, alpha=0.4)



for tech, group in gesdb_conus.groupby("Subsystems.0.Storage Device.Technology Mid-Type"):
    color = gesdb_color_map.get(tech, "gray")
    size = (np.log1p(group["Rated Power (kW)"].fillna(100) / 1000) * 20 + 5).clip(lower=2)
    group.plot(ax=ax, color=color, markersize=size, alpha=0.7,
               label=tech, zorder=3)

size_legend_handles = [
    Line2D([0], [0], marker='o', color='w', markerfacecolor='gray',
           markersize=s, alpha=0.7, label=label)
    for s, label in [(3, "< 1 MW"), (8, "100 MW"), (15, "> 1 GW")]
]

legend_handles = [mpatches.Patch(color=c, label=t) for t, c in gesdb_color_map.items()]

legend1 = ax.legend(handles=legend_handles, bbox_to_anchor=(0.78, 0.45), 
                    loc="upper left", fontsize=14, title="Technology")
ax.add_artist(legend1)

ax.legend(handles=size_legend_handles, bbox_to_anchor=(0.88, 0.6),
          loc="upper left", fontsize=14, title="Rated Power (MW)")

ax.set_axis_off()
fig.tight_layout()
fig.savefig("Projects_policy_map.png", dpi=300, bbox_inches="tight")

print(gesdb_conus.groupby("Subsystems.0.Storage Device.Technology Mid-Type")["Rated Power (kW)"].median() / 1000)