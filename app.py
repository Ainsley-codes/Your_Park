import pandas as pd
import streamlit as st
import geopandas as gpd
import plotly.express as px
import leafmap.foliumap as leafmap

st.set_page_config("Conservation Operations Dashboard", layout="wide")

# ---------------------------
# Load shapefile
# ---------------------------

@st.cache_data
def load_data():
    # --- Operations (polygons, general work) ---
    ops = gpd.read_file("data/operations.shp").to_crs(27700)

    # --- Paths (lines, path maintenance) ---
    paths = gpd.read_file("data2/paths.shp").to_crs(27700)

    # ---------------------------
    # Normalise schemas
    # ---------------------------

    for gdf in [ops, paths]:
        for col in ["Client", "Task_Type", "Site_Name"]:
            gdf[col] = (
                gdf[col]
                .astype(str)
                .str.strip()
                .replace({"": None, "nan": None, "None": None})
            )

        gdf["area_m2"] = 0.0
        gdf["length_m"] = 0.0
        gdf["feature_count"] = 1

        geom = gdf.geom_type
        gdf.loc[geom.isin(["Polygon", "MultiPolygon"]), "area_m2"] = (
            gdf.loc[geom.isin(["Polygon", "MultiPolygon"])].area
        )
        gdf.loc[geom.isin(["LineString", "MultiLineString"]), "length_m"] = (
            gdf.loc[geom.isin(["LineString", "MultiLineString"])].length
        )

    # ---------------------------
    # Combine datasets
    # ---------------------------

    combined = gpd.GeoDataFrame(
        pd.concat([ops, paths], ignore_index=True),
        crs=ops.crs,
    )

    return combined

gdf = load_data()

# ---------------------------
# Validate required fields
# ---------------------------

required_fields = ["Site_Name", "Task_Type", "Client"]
missing = [c for c in required_fields if c not in gdf.columns]

if missing:
    st.error(f"Missing required fields: {missing}")
    st.write("Columns found:", list(gdf.columns))
    st.stop()

# ---------------------------
# Sidebar filters
# ---------------------------

st.sidebar.title("Filters")

clients = sorted(gdf["Client"].dropna().unique())
sites = sorted(gdf["Site_Name"].dropna().unique())
tasks = sorted(gdf["Task_Type"].dropna().unique())

client_sel = st.sidebar.multiselect("Client", clients, default=clients)
site_sel = st.sidebar.multiselect("Site_Name", sites, default=sites)
task_sel = st.sidebar.multiselect("Task Type", tasks, default=tasks)

df = gdf[
    gdf["Client"].isin(client_sel)
    & gdf["Site_Name"].isin(site_sel)
    & gdf["Task_Type"].isin(task_sel)
].copy()

# ---------------------------
# KPI highlights
# ---------------------------

st.title("Your Parks Impact on Green Spaces")

total_area = df["area_m2"].sum()
total_length = df["length_m"].sum()

k1, k2, k3, k4 = st.columns(4)
k1.metric("Clients", df["Client"].nunique())
k2.metric("Sites", df["Site_Name"].nunique())
k3.metric("Area managed (m²)", f"{total_area:,.0f}")
k4.metric("Path length (m)", f"{total_length:,.0f}")

# ---------------------------
# Summary table
# ---------------------------

summary = (
    df.groupby(["Client", "Task_Type", "Site_Name", "Date"], as_index=False)
    .agg(
        area_m2=("area_m2", "sum"),
        length_m=("length_m", "sum"),
    )
)

summary["Date"] = pd.to_datetime(summary["Date"], errors="coerce").dt.date

st.subheader("Client → Task → Site totals")
st.dataframe(summary, use_container_width=True)

area_tasks = summary[summary["area_m2"] > 0]
length_tasks = summary[summary["length_m"] > 0]

# ---------------------------
# Charts
# ---------------------------

st.subheader("Benefits to Bristol & Bath")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🌿 Area-based Conservation Work (m²)")
    fig_area = px.bar(
        area_tasks.groupby("Task_Type", as_index=False).sum(),
        x="Task_Type",
        y="area_m2",
        labels={"area_m2": "Area managed (m²)"},
    )
    st.plotly_chart(fig_area, use_container_width=True)

with col2:
    st.markdown("### 🚶 Path & Linear Maintenance (m)")
    fig_length = px.bar(
        length_tasks.groupby("Task_Type", as_index=False).sum(),
        x="Task_Type",
        y="length_m",
        labels={"length_m": "Length maintained (m)"},
    )
    st.plotly_chart(fig_length, use_container_width=True)


# ---------------------------
# Map
# ---------------------------

st.subheader("Map")

# Prepare data for display
map_df = df.copy()

map_df["Area_m2"] = map_df["area_m2"].round(0)
map_df["Length_m"] = map_df["length_m"].round(0)

# Keep only fields we want users to see
display_fields = [
    "Client",
    "Task_Type",
    "Site_Name",
    "Area_m2",
    "Length_m",
    "geometry",
]

map_df = map_df[display_fields]

# Convert to GeoJSON for reliable popups
geojson = map_df.to_crs(4326).__geo_interface__

m = leafmap.Map()

m.add_geojson(
    geojson,
    layer_name="Operations",
    popup_fields=[
        "Client",
        "Task_Type",
        "Site_Name",
        "Area_m2",
        "Length_m",
    ],
)

m.to_streamlit(height=520)

