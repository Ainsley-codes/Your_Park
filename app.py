import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import leafmap.foliumap as leafmap
from PIL import Image

# --------------------------------------------------
# PAGE CONFIG + LOGO
# --------------------------------------------------
st.set_page_config("Your Park Impact on Green Spaces", layout="wide")

logo = Image.open("yourpark.jpg")
st.image(logo, width=200)

# --------------------------------------------------
# HEADERS + TITLE STYLE
# --------------------------------------------------
st.markdown(
    """
    <style>


    .section-title {
        font-size: 28px;
        font-weight: 800;
        color: #0047AB;
        padding-bottom: 4px;
        border-bottom: 3px solid #F4B000;
        margin-bottom: 20px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)



# --------------------------------------------------
# LOAD DATA
# --------------------------------------------------
@st.cache_data
def load_data():

    ops = gpd.read_file("data/operations.shp").to_crs(27700)
    paths = gpd.read_file("data2/paths.shp").to_crs(27700)

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

    combined = gpd.GeoDataFrame(
        pd.concat([ops, paths], ignore_index=True),
        crs=ops.crs,
    )

    return combined


gdf = load_data()


# --------------------------------------------------
# SIDEBAR FILTERS
# --------------------------------------------------
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


# --------------------------------------------------
# KPI SECTION
# --------------------------------------------------
total_area = df["area_m2"].sum()
total_length = df["length_m"].sum()

st.markdown("<div class='section-title'>💡 Your Park Impact on Green Spaces</div>", unsafe_allow_html=True)

k1, k2, k3 = st.columns(3)
k1.metric("Sites", df["Site_Name"].nunique())
k2.metric("Area managed (m²)", f"{total_area:,.0f}")
k3.metric("Paths cleared (m)", f"{total_length:,.0f}")

st.markdown("<div class='section-separator'></div>", unsafe_allow_html=True)

# --------------------------------------------------
# SUMMARY TABLE
# --------------------------------------------------
summary = (
    df.groupby(["Client", "Task_Type", "Site_Name", "Date"], as_index=False)
    .agg(
        area_m2=("area_m2", "sum"),
        length_m=("length_m", "sum"),
    )
)

summary["Date"] = pd.to_datetime(summary["Date"], errors="coerce").dt.date

st.markdown("<p class='section-title'>📊 Reporting Totals</p>", unsafe_allow_html=True)
st.dataframe(summary, use_container_width=True, hide_index=True)


# --------------------------------------------------
# CHARTS SPLIT
# --------------------------------------------------
area_tasks = summary[summary["area_m2"] > 0]
length_tasks = summary[summary["length_m"] > 0]

st.markdown("<p class='section-title'>🌿 Benefits to Bristol & Bath</p>", unsafe_allow_html=True)

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Area-based habitat care")
    fig1 = px.bar(
        area_tasks.groupby("Task_Type", as_index=False).sum(),
        x="Task_Type",
        y="area_m2",
    )
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.markdown("#### Path maintenance (meters cleared)")
    fig2 = px.bar(
        length_tasks.groupby("Task_Type", as_index=False).sum(),
        x="Task_Type",
        y="length_m",
    )
    st.plotly_chart(fig2, use_container_width=True)


# --------------------------------------------------
# MAP
# --------------------------------------------------
st.markdown("<p class='section-title'>🗺️ Map</p>", unsafe_allow_html=True)

map_df = df.copy()
map_df["Area_m2"] = map_df["area_m2"].round(0)
map_df["Length_m"] = map_df["length_m"].round(0)

display_fields = [
    "Client",
    "Task_Type",
    "Site_Name",
    "Area_m2",
    "Length_m",
    "geometry",
]

geojson = map_df[display_fields].to_crs(4326).__geo_interface__

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
