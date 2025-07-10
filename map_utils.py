import streamlit as st
import pydeck as pdk

def show_invasive_map(invasive_map_df, width=800, height=600):
    """
    Display an interactive heatmap of invasive species points using pydeck (Deck.gl).
    """
    if invasive_map_df.empty or not {'lat', 'lon'}.issubset(invasive_map_df.columns):
        st.info("No map data available.")
        return
    df = invasive_map_df.dropna(subset=['lat', 'lon']).copy()
    if df.empty:
        st.info("No valid map coordinates available.")
        return
    layer = pdk.Layer(
        "HeatmapLayer",
        data=df,
        opacity=0.9,
        radius_scale=6,
        radius_min_pixels=1,
        radius_max_pixels=100,
        get_position='[lon, lat]'
    )
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(),
        longitude=df['lon'].mean(),
        zoom=5,
        pitch=0,
    )
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        map_style='road'
    )
    st.pydeck_chart(deck, use_container_width=True)
