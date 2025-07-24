# ...existing code...
import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import re
import numpy as np
from src.map_utils import show_invasive_map
from src.wikipedia_utils import get_wikipedia_summary

# --- Session-level caching for invasive species results ---
def get_invasive_species_results_cached(scientific_name, fetch_func):
    """
    Retrieve invasive species results for a given scientific name, using session cache to avoid redundant API/database calls.
    fetch_func: function to call if results are not cached. Should accept scientific_name as argument.
    """
    cache_key = f"invasive_results_{scientific_name}"
    if cache_key in st.session_state:
        return st.session_state[cache_key]
    results = fetch_func(scientific_name)
    st.session_state[cache_key] = results
    return results

def show_aggrid(df: pd.DataFrame, grid_key: str = "plant_grid"):
    """Display a DataFrame in an interactive AgGrid table with dynamic column widths."""
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('single', use_checkbox=False)
    for col in df.columns:
        min_width = max(120, len(str(col)) * 10 + 32)
        gb.configure_column(col, minWidth=min_width, autoWidth=True)
    grid_options = gb.build()
    grid_height = min(500, max(150, 35 * (len(df) + 1)))
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.NO_UPDATE,
        theme='streamlit',
        height=grid_height,
        fit_columns_on_grid_load=True,
        key=grid_key
    )
    return grid_response

def normalize_name(n):
    if not isinstance(n, str):
        return ''
    n = n.replace('\ud83c\udfde\ufe0f', '').strip().lower()
    n = re.sub(r'[^a-z0-9 ]+', '', n)
    n = re.sub(r'\s+', ' ', n)
    return n

def show_plantnet_tab(plantnet_df):
    st.markdown("### PlantNet Identification Results")
    if not plantnet_df.empty:
        show_aggrid(plantnet_df, grid_key="plantnet_grid")
    else:
        st.info("No PlantNet results to display.")

def show_forest_tab(invasive_df):
    st.markdown("### Invasive Species Table (Forest Service)")
    if not invasive_df.empty:
        show_aggrid(invasive_df, grid_key="invasive_grid")
    else:
        st.info("No invasive species records found.")

def show_summary_tab(summary_df):
    st.markdown("### Summary by Forest Name")
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("No summary available.")

def show_map_wikipedia_tab(invasive_map_df, selected_scientific_name):
    from src.wikipedia_utils import get_wikipedia_summary
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("### Invasive Species Map")
        show_invasive_map(invasive_map_df)
    with col2:
        st.markdown("### Wikipedia Info")
        wiki = get_wikipedia_summary(selected_scientific_name)
        if wiki:
            st.markdown(f"#### [{wiki.get('title', selected_scientific_name)}]({wiki.get('content_urls',{}).get('desktop',{}).get('page','')})")
            if wiki.get('thumbnail') and wiki['thumbnail'].get('source'):
                st.image(wiki['thumbnail']['source'], width=200)
            st.markdown(wiki.get('extract', 'No summary available.'))
        else:
            st.info("No Wikipedia summary found.")

def show_wikipedia_tab(selected_scientific_name):
    st.markdown("### Wikipedia Info")
    wiki = get_wikipedia_summary(selected_scientific_name)
    if wiki:
        st.markdown(f"#### [{wiki.get('title', selected_scientific_name)}]({wiki.get('content_urls',{}).get('desktop',{}).get('page','')})")
        if wiki.get('thumbnail') and wiki['thumbnail'].get('source'):
            st.image(wiki['thumbnail']['source'], width=200)
        st.markdown(wiki.get('extract', 'No summary available.'))
    else:
        st.info("No Wikipedia summary found.")

def show_full_results(plantnet_df, invasive_df, summary_df, invasive_map_df, selected_scientific_name):
    tab1, tab2, tab3, tab4 = st.tabs([
        "PlantNet Table", "Forest Table", "Summary Table", "Map & Wikipedia"
    ])
    with tab1:
        show_plantnet_tab(plantnet_df)
    with tab2:
        df = st.session_state.get('invasive_df', invasive_df)
        # Convert any ISO 8601 date columns to yyyy-mm-dd
        if isinstance(df, pd.DataFrame):
            for col in df.columns:
                if df[col].dtype == object and df[col].astype(str).str.match(r'^\d{4}-\d{2}-\d{2}T').any():
                    # Column contains ISO 8601 dates, convert to yyyy-mm-dd
                    df[col] = pd.to_datetime(df[col], errors='coerce').dt.strftime('%Y-%m-%d')
        show_forest_tab(df)
    with tab3:
        summary = st.session_state.get('summary_df', summary_df)
        show_summary_tab(summary)
    with tab4:
        map_df = st.session_state.get('invasive_map_df', invasive_map_df)
        sci_name = st.session_state.get('selected_scientific_name', selected_scientific_name)
        show_map_wikipedia_tab(map_df, sci_name)
