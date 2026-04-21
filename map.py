"""
US Grid-scale energy storage status and policy analysis

@author: Yining Wang
"""

# This script maps energy storage data from GESDB and analyzes spatial distribution.

import pandas as pd
import matplotlib.pyplot as plt

plt.rcParams["figure.dpi"] = 300

gesdb = pd.read_csv("GESDB_Project_Data_full.csv")

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
ax1.set_xlabel("Discharge Duration (hrs)")
ax1.set_ylabel("Count")
ax1.set_title("Distribution of Discharge Duration (≤24 hrs)")
ax1.axvline(x=4, color='orange', linestyle='--', label="4-hr threshold")
ax1.axvline(x=10, color='red', linestyle='--', label="10-hr threshold (LDES)")
ax1.legend()

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
ax2.set_xlabel("Discharge Duration (hrs)")
ax2.set_ylabel("")
ax2.set_title("Duration Distribution by Technology")
ax2.legend()

plt.tight_layout()
plt.show()

fig.savefig("GESDB_Duration.png")

#%% Read state boundary and transmission line shapefiles.

import geopandas as gpd

states = gpd.read_file("tl_2024_us_state.zip")
print(states.crs)
print(states.columns.tolist())

transmission = gpd.read_file("US_Electric_Power_Transmission_Lines_1178057934560076066.gpkg")
print(transmission.crs)
print(transmission.columns.tolist())

#%%

states = states.to_crs("EPSG:4326")
transmission = transmission.to_crs("EPSG:4326")

print(transmission["VOLT_CLASS"].value_counts())

high_voltage = transmission[transmission["VOLT_CLASS"].isin(["345", "500", "735 AND ABOVE"])]
print(f"High voltage lines: {len(high_voltage)}")

gesdb_geo = gpd.GeoDataFrame(
    gesdb_op,
    geometry=gpd.points_from_xy(gesdb_op["Longitude"], gesdb_op["Latitude"]),
    crs="EPSG:4326"
)

gesdb_geo = gesdb_geo.dropna(subset=["Latitude", "Longitude"])
print(f"Projects with coordinates: {len(gesdb_geo)}")

#%%

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

states_conus = states[~states["STUSPS"].isin(["AK", "HI", "PR", "GU", "VI", "MP", "AS"])]
gesdb_conus = gesdb_geo[~gesdb_geo["State/Province"].isin(["AK", "HI", "PR", "GU", "VI", "MP", "AS"])]
gesdb_conus = gesdb_geo[
    (gesdb_geo["Longitude"] >= -130) & 
    (gesdb_geo["Longitude"] <= -60) &
    (gesdb_geo["Latitude"] >= 24) & 
    (gesdb_geo["Latitude"] <= 50)
].copy()
gesdb_conus["color"] = gesdb_conus["Subsystems.0.Storage Device.Technology Mid-Type"].map(gesdb_color_map)

gesdb_conus["duration_plot"] = gesdb_conus["Discharge Duration at Rated Power (hrs)"].clip(upper=50).fillna(2)
gesdb_conus["markersize"] = gesdb_conus["duration_plot"] * 3 + 5  

print(f"CONUS projects: {len(gesdb_conus)}")
transmission_conus = high_voltage.clip(states_conus.union_all())

fig, ax = plt.subplots(figsize=(16, 10))

states_conus.plot(ax=ax, color="whitesmoke", edgecolor="gray", linewidth=0.5)

transmission_conus.plot(ax=ax, color="lightblue", linewidth=1, alpha=1, label="Transmission Lines (≥345kV)")

for tech, group in gesdb_conus.groupby("Subsystems.0.Storage Device.Technology Mid-Type"):
    group.plot(ax=ax, color=gesdb_color_map.get(tech, "gray"),
               markersize=group["markersize"],
               alpha=0.7, label=tech)

ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize=8, markerscale=0.5)

ax.set_title("US Grid-Scale Energy Storage Projects and High-Voltage Transmission Lines")
ax.set_axis_off()
plt.tight_layout()
plt.show()

fig.savefig("Installation_map.png")

#%%

rto_stats = gesdb_conus.groupby("ISO/RTO").agg(
    n_projects=("ID", "count"),
    total_capacity_mwh=("Storage Capacity (kWh)", "sum")
).reset_index()

rto_stats["total_capacity_mwh"] = rto_stats["total_capacity_mwh"] / 1000

rto_stats = rto_stats.sort_values("total_capacity_mwh", ascending=False)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

rto_stats.plot(kind="bar", x="ISO/RTO", y="n_projects", ax=ax1, color="steelblue", legend=False)
ax1.set_xlabel("ISO/RTO")
ax1.set_ylabel("Number of Projects")
ax1.set_title("Energy Storage Projects by ISO/RTO")
ax1.tick_params(axis='x', rotation=45)

rto_stats.plot(kind="bar", x="ISO/RTO", y="total_capacity_mwh", ax=ax2, color="orange", legend=False)
ax2.set_xlabel("ISO/RTO")
ax2.set_ylabel("Total Storage Capacity (MWh)")
ax2.set_title("Energy Storage Capacity by ISO/RTO")
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.show()

#%%

gap = panel[panel["year"] == 2024].copy()

panel["re_capacity_mw"] = panel["wind_mw"] + panel["solar_mw"]

gap["re_per_storage"] = gap["re_capacity_mw"] / (gap["energy_total"] / 1000 + 1)
gap = gap.sort_values("re_per_storage", ascending=False)
print(gap[["State", "re_capacity_mw", "energy_total", "re_per_storage"]].head(15))

gap_map = states_conus.merge(
    gap[["State", "re_per_storage"]], 
    left_on="STUSPS", right_on="State", 
    how="left"
)

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
                    ha="center", va="center", fontsize=6, color="black")

ax.set_title("Renewable Energy vs Energy Storage Gap by State (2024)")
ax.set_axis_off()
plt.tight_layout()
plt.show()

fig.savefig("Gap_map.png")

#%% Finally, check function

app_cols = [c for c in gesdb_op.columns if "Applications" in c]
print(app_cols)

for col in app_cols:
    count = gesdb_op[col].notna().sum()
    if count > 0:
        print(f"{col}: {count}")
        print(f"  Values: {gesdb_op[col].dropna().unique()[:5]}")
        
#%%

all_apps = pd.Series(dtype=str)
for col in app_cols:
    all_apps = pd.concat([all_apps, gesdb_op[col].dropna()])

app_counts = all_apps.value_counts()
print(app_counts)

#%%

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

# heatmap: tech vs service
heatmap_data = app_long.groupby(["service", "tech"]).size().unstack(fill_value=0)

fig, ax = plt.subplots(figsize=(14, 10))
sns.heatmap(heatmap_data, ax=ax, cmap="YlOrRd", 
            linewidths=0.5, annot=True, fmt="d",
            cbar_kws={"label": "Number of Projects"})
ax.set_title("Energy Storage Applications by Technology")
ax.set_xlabel("Technology")
ax.set_ylabel("Service")
plt.tight_layout()
plt.show()

fig.savefig("Service_heatmap.png")