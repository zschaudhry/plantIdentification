import streamlit as st
import requests
import os
from dotenv import load_dotenv
import pandas as pd
from typing import Optional
from invasive_utils import show_aggrid

# Load environment variables from .env file
load_dotenv()

# --- UI Title ---
st.title("🌿 Plant Species Identifier 🌿")
st.write("📷 Upload a plant image to identify its species using the Pl@ntNet API and see if it's invasive! 🦠")


# --- Utility Functions ---
def get_api_key() -> Optional[str]:
    api_key = os.getenv("PLANTNET_API_KEY")
    if not api_key:
        st.error("Pl@ntNet API key not found. Please set PLANTNET_API_KEY in your .env file.")
        return None
    return api_key


@st.cache_data(show_spinner=False)
def identify_plant(image_file, organ, api_key):
    url = f"https://my-api.plantnet.org/v2/identify/all?api-key={api_key}"
    files = {'images': (image_file.name, image_file, image_file.type)}
    # Always send a list for 'organs' for consistency and API clarity
    data = {'organs': [organ] if organ != 'auto' else ['auto']}
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Pl@ntNet API request failed: {e}")
        return None


def build_results_dataframe(results) -> pd.DataFrame:
    table_data = []
    for res in results:
        species = res['species'].get('scientificNameWithoutAuthor', '')
        common_names = ', '.join(res['species'].get('commonNames', []))
        genus = res['species'].get('genus', {}).get('scientificNameWithoutAuthor', '')
        family = res['species'].get('family', {}).get('scientificNameWithoutAuthor', '')
        score = res.get('score', 0)
        table_data.append({
            'Scientific Name': species,
            'Common Names': common_names,
            'Genus': genus,
            'Family': family,
            'Confidence Score': f"{score:.2f}"
        })
    return pd.DataFrame(table_data)


def query_invasive_species_database(scientific_name):
    url = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_InvasiveSpecies_01/MapServer/0/query"
    out_fields = [
        "NRCS_PLANT_CODE", "SCIENTIFIC_NAME", "COMMON_NAME", "PROJECT_CODE", "PLANT_STATUS",
        "FS_UNIT_NAME", "EXAMINERS", "LAST_UPDATE"
    ]
    params = {
        'where': f"SCIENTIFIC_NAME='{scientific_name}'",
        'outFields': ",".join(out_fields),
        'returnGeometry': 'true',
        'f': 'json'
    }
    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None


# --- Tab Functions ---
def show_plantnet_tab(plantnet_df, scientific_names):
    st.markdown("### 🌱 PlantNet Identification Results")
    if not plantnet_df.empty:
        selected_name = st.selectbox(
            "🔬 Select a scientific name:",
            scientific_names,
            key="plantnet_scientific_name_select"
        )
        selected_row = plantnet_df[plantnet_df['Scientific Name'] == selected_name].iloc[0].to_dict() if selected_name in plantnet_df['Scientific Name'].values else plantnet_df.iloc[0].to_dict()
        if 'toxicity_show_more' in st.session_state and st.session_state.get('last_selected_name') != selected_name:
            st.session_state['toxicity_show_more'] = False
        st.session_state['last_selected_name'] = selected_name
        if not selected_name:
            st.info("Select a scientific name from the dropdown to see its details below.")
            return None
        st.markdown("#### 🪴 Selected Plant Details")
        for k, v in selected_row.items():
            st.write(f"**{k}:** {v}")
        return selected_name
    else:
        st.info("ℹ️ No PlantNet results to display.")
        return None


def show_forest_tab(invasive_df):
    st.markdown("### 🌲 Invasive Species Table (Forest Service)")
    if not invasive_df.empty:
        # Convert and sort by 'Updated' column if present
        for col in invasive_df.columns:
            col_dtype = invasive_df[col].dtype
            if pd.api.types.is_object_dtype(col_dtype):
                sample = invasive_df[col].dropna().astype(str).head(10)
                if sample.str.match(r"^\d{4}-\d{2}-\d{2}T").any() or sample.str.match(r"^\d{4}-\d{2}-\d{2}$").any():
                    invasive_df[col] = pd.to_datetime(invasive_df[col], errors='coerce').dt.strftime('%Y-%m-%d')
                elif sample.str.match(r"^\d{12,}").any() or sample.str.match(r"^\d{10,}").any():
                    dt = pd.to_datetime(invasive_df[col], errors='coerce', unit='ms')
                    if dt.isna().all():
                        dt = pd.to_datetime(invasive_df[col], errors='coerce', unit='s')
                    invasive_df[col] = dt.dt.strftime('%Y-%m-%d')
            elif pd.api.types.is_integer_dtype(col_dtype) or pd.api.types.is_float_dtype(col_dtype):
                sample = invasive_df[col].dropna().astype(str).head(10)
                if sample.str.match(r"^\d{12,}").any() or sample.str.match(r"^\d{10,}").any():
                    dt = pd.to_datetime(invasive_df[col], errors='coerce', unit='ms')
                    if dt.isna().all():
                        dt = pd.to_datetime(invasive_df[col], errors='coerce', unit='s')
                    invasive_df[col] = dt.dt.strftime('%Y-%m-%d')
        if 'Updated' in invasive_df.columns:
            try:
                invasive_df['Updated_sort'] = pd.to_datetime(invasive_df['Updated'], errors='coerce')
                invasive_df = invasive_df.sort_values('Updated_sort', ascending=False).drop(columns=['Updated_sort'])
            except Exception:
                pass
        show_aggrid(invasive_df, grid_key="invasive_grid")
    else:
        st.info("ℹ️ No invasive species records found.")


def show_summary_tab(summary_df):
    st.markdown("### 📊 Summary by Forest Name")
    if not summary_df.empty:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ No summary available.")


def show_map_tab(invasive_map_df):
    st.markdown("### 🗺️ Invasive Species Map")
    from map_utils import show_invasive_map
    if not invasive_map_df.empty and {'lat', 'lon'}.issubset(invasive_map_df.columns):
        show_invasive_map(invasive_map_df, width=800, height=600)
    else:
        st.info("🗺️ No map data available for this species.")


def show_wikipedia_tab(selected_scientific_name):
    from wikipedia_utils import get_wikipedia_summary
    st.markdown("### 📚 Wikipedia Info")
    if selected_scientific_name:
        wiki = get_wikipedia_summary(selected_scientific_name)
        if wiki:
            st.markdown(f"#### [{wiki.get('title', selected_scientific_name)}]({wiki.get('content_urls',{}).get('desktop',{}).get('page','')}) 📖")
            if wiki.get('thumbnail') and wiki['thumbnail'].get('source'):
                st.image(wiki['thumbnail']['source'], width=200)
            st.markdown(wiki.get('extract', 'No summary available.'))
        else:
            st.info("ℹ️ No Wikipedia summary found.")
    else:
        st.info("ℹ️ No plant selected for Wikipedia lookup.")


# --- Main App Logic ---
def main():
    uploaded_file = st.sidebar.file_uploader("Upload an image...", type=["jpg", "jpeg", "png"])
    if not uploaded_file:
        st.info("Please upload an image to begin.")
        return
    st.image(uploaded_file, caption="Uploaded plant image", width=150)
    api_key = get_api_key()
    if not api_key:
        return
    organ_options = ["auto", "leaf", "flower", "fruit", "bark"]
    organ = st.selectbox(
        "🌱 Select the organ shown in the image:",
        organ_options,
        index=0,
        help="🌸 Choose the plant part most visible in your photo for best results."
    )
    with st.spinner("🔎 Identifying..."):
        result = identify_plant(uploaded_file, organ, api_key)
    if not result or 'results' not in result or not isinstance(result['results'], list) or len(result['results']) == 0:
        st.warning("❌ No species identified by the Pl@ntNet API. Please try another image or check your input.")
        return
    df = build_results_dataframe(result['results'])
    plantnet_df = df.copy()
    invasive_df = pd.DataFrame()
    summary_df = pd.DataFrame()
    invasive_map_df = pd.DataFrame()
    selected_scientific_name = None
    scientific_names = df['Scientific Name'].tolist() if 'Scientific Name' in df.columns else []
    if not scientific_names:
        st.warning("❌ No scientific names found in results.")
        return
    # Query invasive species database for the selected scientific name (will be set in Tab 1)
    fs_results = None
    import invasive_utils as iu
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🌱 Pl@ntNet Data",
        "🌲 Forest Table",
        "📊 Summary Table",
        "🗺️ Map",
        "📚 Wikipedia Info"
    ])
    with tab1:
        selected_scientific_name = show_plantnet_tab(plantnet_df, scientific_names)
        if selected_scientific_name:
            fs_results = query_invasive_species_database(selected_scientific_name)
            if fs_results:
                features = fs_results.get('features', [])
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
                invasive_points = []
                for feature in features:
                    attributes = feature.get('attributes', {})
                    row = {label: attributes.get(key, '') for key, label in FIELD_LABELS.items()}
                    data.append(row)
                    geom = feature.get('geometry', {})
                    name = attributes.get('FS_UNIT_NAME', '')
                    if 'x' in geom and 'y' in geom:
                        lon, lat = geom['x'], geom['y']
                        invasive_points.append({'lat': lat, 'lon': lon, 'orig_name': name})
                    elif 'rings' in geom and geom['rings']:
                        largest_ring = max(geom['rings'], key=lambda ring: len(ring))
                        xs = [pt[0] for pt in largest_ring]
                        ys = [pt[1] for pt in largest_ring]
                        lon = float(sum(xs) / len(xs))
                        lat = float(sum(ys) / len(ys))
                        invasive_points.append({'lat': lat, 'lon': lon, 'orig_name': name})
                invasive_df = pd.DataFrame(data)
                invasive_map_df = pd.DataFrame(invasive_points)
                unit_col = '🏞️ Forest Name'
                if unit_col in invasive_df.columns:
                    summary_df = invasive_df.groupby(unit_col).size().reset_index(name='🧾 Record Count')
                    summary_df = summary_df.sort_values('🧾 Record Count', ascending=False)
            st.session_state['invasive_df'] = invasive_df
            st.session_state['summary_df'] = summary_df
            st.session_state['invasive_map_df'] = invasive_map_df
            st.session_state['selected_scientific_name'] = selected_scientific_name
    with tab2:
        show_forest_tab(st.session_state.get('invasive_df', pd.DataFrame()))
    with tab3:
        show_summary_tab(st.session_state.get('summary_df', pd.DataFrame()))
    with tab4:
        show_map_tab(st.session_state.get('invasive_map_df', pd.DataFrame()))
    with tab5:
        show_wikipedia_tab(st.session_state.get('selected_scientific_name', None))


if __name__ == "__main__":
    main()
    st.markdown('<hr style="margin-top:2em;margin-bottom:0.5em;">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; color:gray; font-size:0.95em;">✨ Developed by Awesome People ✨</div>', unsafe_allow_html=True)
