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
    df = invasive_map_df.dropna(subset=['lat', 'lon']).copy()
    if df.empty:
        st.info("No valid map coordinates available.")
        return
    # Ensure columns for default tooltip: 'Forest Name' and 'Scientific Name'
    if 'Forest Name' not in df.columns:
        if 'orig_name' in df.columns:
            df['Forest Name'] = df['orig_name']
        else:
            df['Forest Name'] = ''
    if 'Scientific Name' not in df.columns:
        sci_cols = [c for c in df.columns if 'scientific' in c.lower()]
        if sci_cols:
            df['Scientific Name'] = df[sci_cols[0]]
        else:
            df['Scientific Name'] = ''
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
        initial_view_state=view_state,
        map_style='road',
        tooltip=True
    )
    st.pydeck_chart(deck, use_container_width=True)
