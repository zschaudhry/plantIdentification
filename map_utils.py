


import pandas as pd
import streamlit as st
import pydeck as pdk

def show_invasive_map(invasive_map_df: pd.DataFrame, width=800, height=600):
    """
    Display an interactive map with invasive species points using pydeck (Deck.gl).
    """
    if invasive_map_df.empty or not {'lat', 'lon'}.issubset(invasive_map_df.columns):
        st.info("No map data available.")
        return
    df = invasive_map_df.dropna(subset=['lat', 'lon'])
    if df.empty:
        st.info("No valid map coordinates available.")
        return
    layer = pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position='[lon, lat]',
        get_radius=5000,
        get_fill_color=[255, 102, 0, 160],
        pickable=True,
        auto_highlight=True,
    )
    view_state = pdk.ViewState(
        latitude=df['lat'].mean(),
        longitude=df['lon'].mean(),
        zoom=5,
        pitch=0,
    )
    deck = pdk.Deck(
        layers=[layer],
        initial_view_state=view_state
    )
    st.pydeck_chart(deck, use_container_width=True)
