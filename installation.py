"""
US Grid-scale energy storage status and policy analysis

@author: Yining Wang
"""

# This script analyzes energy storage installation from EIA 860 form.


import zipfile
import pandas as pd
import os
import matplotlib.pyplot as plt

plt.rcParams["figure.dpi"] = 300

data_path = "Data/EIA/860"

common_cols = [
    'Utility ID', 'Utility Name', 'Plant Code', 'Plant Name', 
    'State', 'County', 'Generator ID', 'Status', 'Technology', 
    'Prime Mover', 'Sector Name', 'Sector',
    'Nameplate Capacity (MW)', 'Summer Capacity (MW)', 'Winter Capacity (MW)',
    'Operating Month', 'Operating Year', 
    'Nameplate Energy Capacity (MWh)',
    'Maximum Charge Rate (MW)', 'Maximum Discharge Rate (MW)',
    'Storage Technology 1', 'Storage Technology 2',
    'Arbitrage', 'Frequency Regulation', 'Load Following',
    'Ramping / Spinning Reserve', 'Co-Located Renewable Firming',
    'Transmission and Distribution Deferral', 'System Peak Shaving',
    'Load Management', 'Voltage or Reactive Power Support',
    'Backup Power', 'Excess Wind and Solar Generation'
]

dfs = []

for year in range(2016, 2025):
    zip_file = os.path.join(data_path, f"eia860{year}.zip")
    with zipfile.ZipFile(zip_file) as z:
        es_file = [f for f in z.namelist() if "Energy_Storage" in f][0]
        with z.open(es_file) as f:
            es = pd.read_excel(f, sheet_name=0, skiprows=1)
            es = es[[c for c in common_cols if c in es.columns]]
            es["year"] = year
            dfs.append(es)
            print(f"{year}: {len(es)} rows")

es_raw = pd.concat(dfs, ignore_index=True)
print(f"\nTotal: {len(es_raw)} rows")

es_raw["Nameplate Capacity (MW)"] = pd.to_numeric(es_raw["Nameplate Capacity (MW)"], errors="coerce")
es_raw["Nameplate Energy Capacity (MWh)"] = pd.to_numeric(es_raw["Nameplate Energy Capacity (MWh)"], errors="coerce")

#%%
es_raw["Storage Technology 1"] = es_raw["Storage Technology 1"].fillna(es_raw["Technology"])
print(es_raw["Storage Technology 1"].value_counts())

type_map = {
    "LIB": "Lithium-ion Battery",
    "NAB": "Sodium-based Battery",
    "Flywheels": "Flywheel",
    "OTH": "Other",
    "PBB": "Lead-acid Battery",
    "NIB": "Nickel-based Battery",
    "Solar Thermal with Energy Storage": "Thermal",
    "FLB": "Flow Battery",
    "Natural Gas with Compressed Air Storage": "Compressed Air",
    "Batteries": "Other Battery",
    "MAB": "Metal-air Battery",
    "ECC": "Electro-chemical Capacitor",
}

es_raw["tech_group"] = es_raw["Storage Technology 1"].map(type_map)

panel = es_raw.groupby(["State", "year"]).agg(
    capacity_total=("Nameplate Capacity (MW)", "sum"),
    energy_total=("Nameplate Energy Capacity (MWh)", "sum"),
    n_units=("Generator ID", "count")
).reset_index()


new_units = es_raw[es_raw["Operating Year"] == es_raw["year"]].groupby(["State", "year"]).agg(
    capacity_new=("Nameplate Capacity (MW)", "sum"),
    n_units_new=("Generator ID", "count")
).reset_index()


panel = panel.merge(new_units, on=["State", "year"], how="left").fillna(0)
print(panel.head())

tech_panel = es_raw.groupby(["year", "tech_group"])["Nameplate Energy Capacity (MWh)"].sum().reset_index()
print(tech_panel)

tech_new = es_raw[es_raw["Operating Year"] == es_raw["year"]].groupby(
    ["year", "tech_group"])["Nameplate Energy Capacity (MWh)"].sum().reset_index()

tech_pivot = tech_panel.pivot(
    index="year", columns="tech_group", 
    values="Nameplate Energy Capacity (MWh)"
).fillna(0)

#%% Import renewable energy data

re_dfs = []

for year in range(2016, 2025):
    zip_file = os.path.join(data_path, f"eia860{year}.zip")
    with zipfile.ZipFile(zip_file) as z:
        for re_type in ["Wind", "Solar"]:
            re_file = [f for f in z.namelist() if re_type in f][0]
            with z.open(re_file) as f:
                re = pd.read_excel(f, sheet_name=0, skiprows=1, 
                                   engine='openpyxl',
                                   usecols=["State", "Status", "Technology",
                                            "Nameplate Capacity (MW)", 
                                            "Operating Year"])
                re["year"] = year
                re["source"] = re_type
                re_dfs.append(re)
                print(f"{year} {re_type}: {len(re)} rows")

re_raw = pd.concat(re_dfs, ignore_index=True)
re_raw["Nameplate Capacity (MW)"] = pd.to_numeric(
    re_raw["Nameplate Capacity (MW)"], errors="coerce")
print(f"\nTotal: {len(re_raw)} rows")


re_panel = re_raw.groupby(["State", "year"])["Nameplate Capacity (MW)"].sum().reset_index()
re_panel = re_panel.rename(columns={"Nameplate Capacity (MW)": "re_capacity_mw"})


panel = panel.merge(re_panel, on=["State", "year"], how="left").fillna(0)
print(panel.head())

re_panel_split = re_raw.groupby(["State", "year", "source"])["Nameplate Capacity (MW)"].sum().reset_index()
re_panel_split = re_panel_split.pivot(index=["State", "year"], columns="source", values="Nameplate Capacity (MW)").reset_index().fillna(0)
re_panel_split = re_panel_split.rename(columns={"Wind": "wind_mw", "Solar": "solar_mw"})

panel = panel.drop(columns=["re_capacity_mw"], errors="ignore")
panel = panel.merge(re_panel_split, on=["State", "year"], how="left").fillna(0)

panel.to_csv("Data/renewable_panel.csv")

#%% Plot ES installation trend, with renewable trend and by type of tech.

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# left, ES capacity with RE trend
total_es = panel.groupby("year")["energy_total"].sum()
total_wind = panel.groupby("year")["wind_mw"].sum()
total_solar = panel.groupby("year")["solar_mw"].sum()

ax1.bar(total_es.index, total_es.values, color="steelblue", label="Energy Storage (MWh)")
ax1_twin = ax1.twinx()

ax1_twin.plot(total_wind.index, total_wind.values, color="orange",
              marker="o", linewidth=2, label="Wind (MW)")
ax1_twin.plot(total_solar.index, total_solar.values, color="gold",
              marker="s", linewidth=2, label="Solar (MW)")

ax1.set_xlabel("Year")
ax1.set_ylabel("Energy Storage Capacity (MWh)")  
ax1_twin.set_ylabel("Renewable Energy Capacity (MW)") 
ax1.set_title("US Energy Storage and Renewable Energy\nCapacity Trend (2016-2024)")
ax1.tick_params(axis='x', rotation=45)

lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax1_twin.get_legend_handles_labels()

ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left")

# right, %ES type

color_map = {
    "Electro-chemical Capacitor": "#2CA02C",
    "Lithium-ion Battery": "#4C72B0",
    "Flywheel": "#DD8452",
    "Thermal": "#55A868",
    "Compressed Air": "#C44E52",
    "Flow Battery": "#8172B3",
    "Lead-acid Battery": "#937860",
    "Nickel-based Battery": "#DA8BC3",
    "Sodium-based Battery": "#8C8C8C",
    "Metal-air Battery": "#CCB974",
    "Other Battery": "#64B5CD",
    "Other": "#1D1D1D",
}

tech_pct = tech_pivot.div(tech_pivot.sum(axis=1), axis=0) * 100

tech_order = tech_pct.iloc[-1].sort_values(ascending=False).index
colors = [color_map[c] for c in tech_order]
tech_pct_sorted = tech_pct[tech_order]
tech_pct_sorted.plot(kind="bar", stacked=True, ax=ax2, color=colors)

ax2.set_xlabel("Year")
ax2.set_ylabel("Share (%)")
ax2.set_title("US Grid-Scale Energy Storage\nTechnology Share (2016-2024)")
ax2.legend(bbox_to_anchor=(1.05, 1), loc="upper left")
ax2.tick_params(axis='x', rotation=45)
handles, labels = ax2.get_legend_handles_labels()
ax2.legend(handles[::-1], labels[::-1], loc="lower right", fontsize=8)

plt.tight_layout()
plt.show()

fig.savefig("ES_install_trend.png")

#%% Plot by type of utility

print(es_raw["Sector Name"].value_counts())

sector_map = {
    "IPP Non-CHP": "IPP",
    "IPP CHP": "IPP",
    "Electric Utility": "Electric Utility",
    "Commercial Non-CHP": "Commercial/\nIndustrial",
    "Commercial CHP": "Commercial/\nIndustrial",
    "Industrial Non-CHP": "Commercial/\nIndustrial",
    "Industrial CHP": "Commercial/\nIndustrial",
}

es_raw["sector_group"] = es_raw["Sector Name"].map(sector_map)

sector_panel = es_raw.groupby(["year", "sector_group"])["Nameplate Energy Capacity (MWh)"].sum().reset_index()
sector_pivot = sector_panel.pivot(index="year", columns="sector_group",
                                   values="Nameplate Energy Capacity (MWh)").fillna(0)

sector_order = sector_pivot.iloc[-1].sort_values(ascending=False).index
sector_pivot_sorted = sector_pivot[sector_order]

tech_sector = es_raw.groupby(["sector_group", "tech_group"])["Nameplate Energy Capacity (MWh)"].sum().reset_index()
tech_sector_pivot = tech_sector.pivot(index="sector_group", columns="tech_group",
                                       values="Nameplate Energy Capacity (MWh)").fillna(0)

tech_sector_pivot = tech_sector_pivot.loc[tech_sector_pivot.sum(axis=1).sort_values(ascending=False).index]

tech_sector_pivot = tech_sector_pivot[tech_order]

tech_sector_pct = tech_sector_pivot.div(tech_sector_pivot.sum(axis=1), axis=0) * 100

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

# left,by sector trend
sector_pivot_sorted.plot(kind="bar", stacked=True, ax=ax1)
handles, labels = ax1.get_legend_handles_labels()
ax1.legend(handles[::-1], labels[::-1], loc="upper left")
ax1.set_xlabel("Year")
ax1.set_ylabel("Nameplate Energy Capacity (MWh)")
ax1.set_title("US Grid-Scale Energy Storage\nby Sector (2016-2024)")
ax1.tick_params(axis='x', rotation=45)

# righ, tech by sector percentage
tech_sector_pct.plot(kind="bar", stacked=True, ax=ax2, color=colors)
handles, labels = ax2.get_legend_handles_labels()
ax2.legend(handles[::-1], labels[::-1], loc="lower right", fontsize=8)
ax2.set_xlabel("Sector")
ax2.set_ylabel("Share (%)")
ax2.set_title("Technology Share by Sector\n(2016-2024 Cumulative)")
ax2.tick_params(axis='x', rotation=0)

plt.tight_layout()
plt.show()

fig.savefig("ES_install_sector.png")