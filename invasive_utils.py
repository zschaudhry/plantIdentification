

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import re
import numpy as np

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
    n = n.replace('🏞️', '').strip().lower()
    n = re.sub(r'[^a-z0-9 ]+', '', n)
    n = re.sub(r'\s+', ' ', n)
    return n

def show_invasive_species_results(fs_results):
    features = fs_results.get('features', [])
    if not features:
        st.info("No invasive species data found for this plant.")
        return

    # --- Extract geometry for map ---
    invasive_points = []
    for feature in features:
        geom = feature.get('geometry', {})
        attrs = feature.get('attributes', {})
        name = attrs.get('FS_UNIT_NAME', '')
        orig_name = name
        # Handle point geometry (already lon/lat)
        if 'x' in geom and 'y' in geom:
            lon, lat = geom['x'], geom['y']
            invasive_points.append({'lat': lat, 'lon': lon, 'orig_name': orig_name})
        # Handle polygon geometry (rings, already lon/lat)
        elif 'rings' in geom and geom['rings']:
            largest_ring = max(geom['rings'], key=lambda ring: len(ring))
            xs = [pt[0] for pt in largest_ring]
            ys = [pt[1] for pt in largest_ring]
            lon = float(np.mean(xs))
            lat = float(np.mean(ys))
            invasive_points.append({'lat': lat, 'lon': lon, 'orig_name': orig_name})

    invasive_map_df = pd.DataFrame(invasive_points)

    # --- Build DataFrame for summary and AgGrid ---
    FIELD_LABELS = {
        'NRCS_PLANT_CODE': '🆔 NRCS Plant Code',
        'SCIENTIFIC_NAME': '🔬 Scientific Name',
        'COMMON_NAME': '🌱 Common Name',
        'PROJECT_CODE': '📁 Project Code',
        'PLANT_STATUS': '🚦 Plant Status',
        'FS_UNIT_NAME': '🏞️ Forest Name',
        'EXAMINERS': '🧑‍🔬 Examiners',
        'LAST_UPDATE': 'Updated',
    }
    data = []
    for feature in features:
        attributes = feature.get('attributes', {})
        row = {}
        for key, label in FIELD_LABELS.items():
            row[label] = attributes.get(key, '')
        data.append(row)
    df = pd.DataFrame(data)

    # --- Convert Last Update from ms timestamp to date if needed ---
    if 'Updated' in df.columns:
        def parse_updated(val):
            if pd.isna(val) or val == '' or str(val).strip() in ['0', '0.0', 'NaT', 'None', 'nan', 'null']:
                return ''
            sval = str(val).strip()
            m = re.match(r"Date\((\d+)\)", sval)
            if m:
                ms = int(m.group(1))
                sval = str(ms)
            try:
                fval = float(sval)
                if fval > 100000000000:
                    dt = pd.to_datetime(fval, unit='ms', errors='coerce')
                elif fval > 1000000000:
                    dt = pd.to_datetime(fval, unit='s', errors='coerce')
                else:
                    dt = pd.to_datetime(sval, errors='coerce')
            except Exception:
                dt = pd.to_datetime(sval, errors='coerce')
            if pd.isna(dt):
                return ''
            return dt.strftime('%Y-%m-%d')
        df['Updated'] = df['Updated'].apply(parse_updated)

    # --- Summary Table and Map by Forest Name ---
    unit_col = '🏞️ Forest Name'
    if 'FS_UNIT_NAME' in df.columns and unit_col not in df.columns:
        df[unit_col] = df['FS_UNIT_NAME']
    selected_unit = 'All'

    # --- Map ---
    if not invasive_map_df.empty:
        st.markdown('## 🗺️ Invasive Species Map ')
        import folium
        from streamlit_folium import st_folium
        m = folium.Map(location=[39.8283, -98.5795], zoom_start=3, tiles='OpenStreetMap')
        for _, row in invasive_map_df.iterrows():
            folium.CircleMarker(
                location=[row['lat'], row['lon']],
                radius=8,
                color='#ff6600',
                fill=True,
                fill_color='#ff6600',
                fill_opacity=0.7,
                tooltip=f"<b>{row['orig_name']}</b>",
                parse_html=True
            ).add_to(m)
        st_folium(m, width=0)

    # --- Summary Table and Filter ---
    if unit_col in df.columns:
        summary = df.groupby(unit_col).size().reset_index(name='🧾 Record Count')
        summary['orig_name'] = summary[unit_col]
        summary['norm_name'] = summary[unit_col].map(normalize_name)
        summary = summary.sort_values('🧾 Record Count', ascending=False)
        st.markdown('## 🏞️ Summary by Forest Name')
        st.dataframe(summary[[unit_col, '🧾 Record Count']], use_container_width=True, hide_index=True)

        all_units = summary[unit_col].dropna().tolist()
        all_units = [u for u in all_units if u]
        selected_unit = st.selectbox('🏞️ Filter by Forest Name', ['All'] + all_units, key='unit_filter')
        if selected_unit != 'All':
            df = df[df[unit_col] == selected_unit]

    # --- Show AgGrid or message if empty ---
    if not df.empty:
        grid_key = f"invasive_species_grid_{selected_unit}"
        show_aggrid(df, grid_key=grid_key)
    else:
        st.info("No records found for the selected Forest Name.")
