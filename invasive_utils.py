
import pandas as pd
import datetime
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
import re
import requests
import numpy as np
from pyproj import Transformer

def show_aggrid(df: pd.DataFrame, grid_key: str = "plant_grid"):
    """Display a DataFrame in an interactive AgGrid table with dynamic column widths."""
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('single', use_checkbox=False)
    # Set minWidth for each column to at least the label width in pixels (estimate: 8px per character + padding)
    for col in df.columns:
        min_width = max(120, len(str(col)) * 10 + 32)  # 10px per char + 32px padding, min 120px
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

def show_invasive_species_results(fs_results):
    features = fs_results['features']
    if not features:
        st.info("No invasive species data found for this plant.")
        return
    # Map short field names to full labels for display (with emojis)
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
            import pandas as pd
            import re
            if pd.isna(val) or val == '' or str(val).strip() in ['0', '0.0', 'NaT', 'None', 'nan', 'null']:
                return ''
            sval = str(val).strip()
            # Handle JavaScript Date(1351618347000) or Date(1351618347)
            m = re.match(r"Date\((\d+)\)", sval)
            if m:
                ms = int(m.group(1))
                val = ms
                sval = str(ms)
            try:
                fval = float(sval)
                if fval > 100000000000:  # ms since epoch
                    dt = pd.to_datetime(fval, unit='ms', errors='coerce')
                elif fval > 1000000000:  # s since epoch
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
    selected_unit = 'All'  # Ensure always defined for grid_key
    if unit_col in df.columns:
        summary = df.groupby(unit_col).size().reset_index(name='🧾 Record Count')
        summary['orig_name'] = summary[unit_col]  # Save original for display
        def normalize_name(n):
            if not isinstance(n, str):
                return ''
            n = n.replace('🏞️', '').strip().lower()
            n = re.sub(r'[^a-z0-9 ]+', '', n)  # Remove punctuation
            n = re.sub(r'\s+', ' ', n)        # Collapse multiple spaces
            return n
        summary['norm_name'] = summary[unit_col].map(normalize_name)
        summary = summary.sort_values('🧾 Record Count', ascending=False)
        st.markdown('## 🏞️ Summary by Forest Name')
        st.dataframe(summary[[unit_col, '🧾 Record Count']], use_container_width=True, hide_index=True)

        # --- Forest Service Unit Name Map Visualization ---
        @st.cache_data(show_spinner=False)
        def fetch_forest_boundaries():
            fs_url = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_ForestSystemBoundaries_01/MapServer/0/query"
            params = {
                'where': '1=1',
                'outFields': 'FORESTNAME',
                'returnGeometry': 'true',
                'f': 'json'
            }
            try:
                resp = requests.get(fs_url, params=params, timeout=40)
                if resp.status_code == 200:
                    return resp.json()
                else:
                    return None
            except requests.exceptions.Timeout:
                st.warning("Forest boundary service timed out. Map will not be shown.")
                return None
            except Exception as e:
                st.warning(f"Error fetching forest boundaries: {e}")
                return None
        geo_data = fetch_forest_boundaries()
        if geo_data is not None:
            # Use the same normalization as above for both sources
            # (function already defined above)

            # Use norm_name for matching, orig_name for display
            summary = summary.copy()
            transformer = Transformer.from_crs(3857, 4326, always_xy=True)
            forest_points = {}
            for feat in geo_data.get('features', []):
                attrs = feat.get('attributes', {})
                name = attrs.get('FORESTNAME')
                norm_name = normalize_name(name)
                if not norm_name:
                    continue
                geom = feat.get('geometry', {})
                # Use centroid of largest ring (polygon) for marker placement
                if 'rings' in geom and geom['rings']:
                    largest_ring = max(geom['rings'], key=lambda ring: len(ring))
                    ring_points = np.array(largest_ring)
                    x, y = ring_points.mean(axis=0)
                elif 'x' in geom and 'y' in geom:
                    x, y = geom['x'], geom['y']
                else:
                    continue
                lon, lat = transformer.transform(x, y)
                forest_points[norm_name] = (lat, lon)
            summary = summary.copy()
            # Only use matched names for the map
            summary['lat'] = summary['norm_name'].map(lambda n: forest_points[n][0] if n in forest_points and not np.isnan(forest_points[n][0]) and not np.isnan(forest_points[n][1]) else np.nan)
            summary['lon'] = summary['norm_name'].map(lambda n: forest_points[n][1] if n in forest_points and not np.isnan(forest_points[n][0]) and not np.isnan(forest_points[n][1]) else np.nan)
            # Use only the rows with valid coordinates for the map (i.e., matched and not NaN)
            summary_map = summary[(~summary['lat'].isna()) & (~summary['lon'].isna())].copy()
            # Warn if any forest names in summary do not have a matching marker
            unmatched = summary[summary['norm_name'].apply(lambda n: n not in forest_points or np.isnan(forest_points.get(n, (np.nan, np.nan))[0]) or np.isnan(forest_points.get(n, (np.nan, np.nan))[1]))]
            matched = summary[~summary.index.isin(unmatched.index)]
            st.info(f"Forest name match stats: {len(matched)} matched, {len(unmatched)} unmatched out of {len(summary)} total.")
            if not unmatched.empty:
                st.warning(f"No map marker for these Forest Names: {', '.join(unmatched['orig_name'].astype(str))}")
            if not summary_map.empty:
                st.markdown('### 🗺️ Forest Map')
                import folium
                from streamlit_folium import st_folium
                # Center map on the United States by default (lat, lon = 39.8283, -98.5795), zoom_start=3
                m = folium.Map(location=[39.8283, -98.5795], zoom_start=3, tiles='OpenStreetMap')
                # Add points
                for _, row in summary_map.iterrows():
                    folium.CircleMarker(
                        location=[row['lat'], row['lon']],
                        radius=int(max(5, min(30, (row['🧾 Record Count'] if row['🧾 Record Count'] > 0 else 1) ** 0.5))),
                        color='#0080ff',
                        fill=True,
                        fill_color='#0080ff',
                        fill_opacity=0.7,
                        tooltip=f"<b>{row['orig_name']}</b><br/>{row['🧾 Record Count']} records",
                        parse_html=True
                    ).add_to(m)
                st_folium(m)
        else:
            st.info("Map service request failed or could not be loaded.")

        # Dropdown filter
        all_units = summary[unit_col].dropna().tolist()
        all_units = [u for u in all_units if u]
        selected_unit = st.selectbox('🏞️ Filter by Forest Name', ['All'] + all_units, key='unit_filter')
        if selected_unit != 'All':
            df = df[df[unit_col] == selected_unit]

    # --- Show AgGrid or message if empty ---
    if not df.empty:
        # Make AgGrid key unique per selected unit (always defined)
        grid_key = f"invasive_species_grid_{selected_unit}"
        show_aggrid(df, grid_key=grid_key)
    else:
        st.info("No records found for the selected Forest Name.")
