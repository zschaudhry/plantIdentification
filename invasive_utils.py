import pandas as pd
import datetime
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

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
        'FS_UNIT_NAME': '🏞️ Forest Service Unit Name',
        'EXAMINERS': '🧑‍🔬 Examiners',
        'LAST_UPDATE': '📅 Last Update',
    }
    data = []
    for feature in features:
        attributes = feature.get('attributes', {})
        row = {}
        for key, label in FIELD_LABELS.items():
            row[label] = attributes.get(key, '')
        data.append(row)
    df = pd.DataFrame(data)
    if 'Last Update' in df.columns:
        def parse_last_update(val):
            if pd.isna(val) or val == '' or str(val).strip() in ['0', '0.0', 'NaT', 'None', 'nan', 'null']:
                return ''
            try:
                ms = float(val)
                if ms > 100000000000:
                    dt = datetime.datetime.utcfromtimestamp(ms / 1000)
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
            try:
                ival = int(float(val))
                if ival > 0 and ival < 10000000000:
                    dt = datetime.datetime.utcfromtimestamp(ival)
                    if dt.year < 1980:
                        return ''
                    return dt.strftime('%Y-%m-%d')
            except Exception:
                pass
            try:
                dt = pd.to_datetime(val, errors='coerce')
                if pd.isna(dt) or dt.year < 1980:
                    return ''
                return dt.strftime('%Y-%m-%d')
            except Exception:
                return str(val)
        df['Last Update'] = df['Last Update'].apply(parse_last_update)
        df['Last Update Sort'] = pd.to_datetime(df['Last Update'], errors='coerce')
        df = df.sort_values('Last Update Sort', ascending=False).drop(columns=['Last Update Sort'])

    # --- Summary Table by Forest Service Unit Name ---
    unit_col = '🏞️ Forest Service Unit Name'
    if unit_col in df.columns:
        summary = df.groupby(unit_col).size().reset_index(name='🧾 Record Count')
        summary = summary.sort_values('🧾 Record Count', ascending=False)
        st.markdown('## 🏞️ Summary by Forest Name')
        st.dataframe(summary, use_container_width=True, hide_index=True)

        # Dropdown filter
        all_units = summary[unit_col].dropna().tolist()
        all_units = [u for u in all_units if u]  # Remove empty strings
        selected_unit = st.selectbox('🏞️ Filter by Forest Service Unit Name', ['All'] + all_units, key='unit_filter')
        if selected_unit != 'All':
            df = df[df[unit_col] == selected_unit]

    show_aggrid(df, grid_key="invasive_species_grid")
