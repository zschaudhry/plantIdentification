import pandas as pd
import datetime
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

def show_aggrid(df: pd.DataFrame, grid_key: str = "plant_grid"):
    """Display a DataFrame in an interactive AgGrid table with dynamic column widths."""
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('single', use_checkbox=False)
    for col in df.columns:
        gb.configure_column(col, autoWidth=True)
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
    data = []
    for feature in features:
        attributes = feature.get('attributes', {})
        last_update_raw = attributes.get('LAST_UPDATE', '')
        data.append({
            'NRCS Plant Code': attributes.get('NRCS_PLANT_CODE', ''),
            'Scientific Name': attributes.get('SCIENTIFIC_NAME', ''),
            'Common Name': attributes.get('COMMON_NAME', ''),
            'Project Code': attributes.get('PROJECT_CODE', ''),
            'Plant Status': attributes.get('PLANT_STATUS', ''),
            'Infested Area (acres)': attributes.get('INFESTED_AREA', 0),
            'Infested Percent': attributes.get('INFESTED_PERCENT', 0),
            'FS Unit Name': attributes.get('FS_UNIT_NAME', ''),
            'Examiners': attributes.get('EXAMINERS', ''),
            'Last Update': last_update_raw
        })
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
    show_aggrid(df, grid_key="invasive_species_grid")
