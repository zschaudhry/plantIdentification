import streamlit as st
import requests
import os
from dotenv import load_dotenv
import pandas as pd
from invasive_utils import show_invasive_species_results
from typing import Optional



from wikipedia_utils import get_wikipedia_section, get_wikipedia_summary
from utils import highlight_toxicity
from invasive_utils import show_aggrid

# Load environment variables from .env file
load_dotenv()

# Streamlit UI Title
st.title("🌿 Plant Species Identifier 🌿")
st.write("📷 Upload a plant image to identify its species using the Pl@ntNet API.")


def get_api_key() -> Optional[str]:
    """Fetch the Pl@ntNet API key from environment variables."""
    api_key = os.getenv("PLANTNET_API_KEY")
    if not api_key:
        st.error("Pl@ntNet API key not found. Please set PLANTNET_API_KEY in your .env file.")
        return None
    return api_key

@st.cache_data(show_spinner=False)
def identify_plant(image_file, organ, api_key):
    """Identify plant species using the Pl@ntNet API. Caches results for identical images/organs/api_key."""
    url = f"https://my-api.plantnet.org/v2/identify/all?api-key={api_key}"
    files = {'images': (image_file.name, image_file, image_file.type)}
    data = {'organs': organ}
    try:
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Pl@ntNet API request failed: {e}")
        return None

def build_results_dataframe(results) -> pd.DataFrame:
    """Build a DataFrame from Pl@ntNet API results."""
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
        "Select the organ shown in the image:",
        organ_options,
        index=0,
        help="Choose the plant part most visible in your photo for best results."
    )
    with st.spinner("Identifying..."):
        result = identify_plant(uploaded_file, organ, api_key)
    if not result or 'results' not in result or not result['results']:
        st.warning("No species identified. Try another image.")
        return

    df = build_results_dataframe(result['results'])
    show_aggrid(df, grid_key="plant_grid")

    scientific_names = df['Scientific Name'].tolist() if 'Scientific Name' in df.columns else []
    if not scientific_names:
        st.warning("No scientific names found in results.")
        return

    selected_name = st.selectbox("Select a scientific name:", scientific_names, index=0)

    # Reset toxicity show more state if a new plant is selected
    if 'toxicity_show_more' in st.session_state and st.session_state.get('last_selected_name') != selected_name:
        st.session_state['toxicity_show_more'] = False
    st.session_state['last_selected_name'] = selected_name
    if not selected_name:
        st.info("Select a scientific name from the dropdown to see its details below.")
        return
    fs_results=query_invasive_species_database(selected_name)
    if fs_results:
        st.markdown("### Invasive Species Information from the Forest Service 🌍")
        show_invasive_species_results(fs_results)
    with st.spinner("Fetching Wikipedia information..."):
        wiki_data = get_wikipedia_summary(selected_name)
    if wiki_data:
        st.markdown(f"### {wiki_data.get('title', selected_name)} 🌱")
        if 'thumbnail' in wiki_data:
            st.image(wiki_data['thumbnail']['source'], width=200)
        description = wiki_data.get('description')
        if description:
            st.markdown(f"**📝 Description:** {description}")
        summary = wiki_data.get('extract')
        if summary:
            st.markdown(f"**📖 Summary:** {summary}")
        timestamp = wiki_data.get('timestamp')
        if timestamp:
            st.markdown(f"**⏰ Last updated:** {timestamp}")

        # --- Invasive Species Section for this species ---
        page_title = wiki_data.get('title', selected_name)
        with st.spinner("Fetching invasive species info..."):
            invasive_section = get_wikipedia_section(page_title, "Invasive species")
        st.markdown('**🦠 Invasive Species (from Wikipedia page):**')
        if invasive_section:
            st.markdown(invasive_section)
        else:
            st.info("No invasive species information available for this plant.")

        # --- Toxicity Section for this species ---
        with st.spinner("Fetching toxicity info..."):
            toxicity_section = get_wikipedia_section(page_title, "Toxicity")
        st.markdown('<div style="font-weight:bold; font-size:1.1em; margin-top:1.5em; margin-bottom:0.5em; color:#b30000;">☠️ Toxicity (from Wikipedia page):</div>', unsafe_allow_html=True)
        if toxicity_section:
            pretty_text = highlight_toxicity(toxicity_section)
            words = pretty_text.split()
            if len(words) > 150:
                short_text = ' '.join(words[:150])
                if 'toxicity_show_more' not in st.session_state:
                    st.session_state['toxicity_show_more'] = False
                if not st.session_state['toxicity_show_more']:
                    st.markdown(f'<blockquote style="background:#fff6f6; border-left:5px solid #b30000; padding:1em 1.5em; border-radius:6px; margin:0 0 1em 0; font-size:1.05em; line-height:1.7; color:#222;">{short_text}...</blockquote>', unsafe_allow_html=True)
                    if st.button('Show more', key='toxicity_show_more_btn'):
                        st.session_state['toxicity_show_more'] = True
                elif st.session_state['toxicity_show_more']:
                    st.markdown(f'<blockquote style="background:#fff6f6; border-left:5px solid #b30000; padding:1em 1.5em; border-radius:6px; margin:0 0 1em 0; font-size:1.05em; line-height:1.7; color:#222;">{pretty_text}</blockquote>', unsafe_allow_html=True)
            else:
                st.markdown(f'<blockquote style="background:#fff6f6; border-left:5px solid #b30000; padding:1em 1.5em; border-radius:6px; margin:0 0 1em 0; font-size:1.05em; line-height:1.7; color:#222;">{pretty_text}</blockquote>', unsafe_allow_html=True)
        else:
            st.info("No toxicity information available for this plant.")

        st.markdown(f"[🔗 Read more on Wikipedia]({wiki_data.get('content_urls', {}).get('desktop', {}).get('page', '')})")

def query_invasive_species_database(scientific_name):
    url = "https://apps.fs.usda.gov/arcx/rest/services/EDW/EDW_InvasiveSpecies_01/MapServer/0/query"
    out_fields = [
        "NRCS_PLANT_CODE",
        "SCIENTIFIC_NAME",
        "COMMON_NAME",
        "PROJECT_CODE",
        "PLANT_STATUS",
        "FS_UNIT_NAME",
        "EXAMINERS",
        "LAST_UPDATE"
    ]
    params = {
        'where': f"SCIENTIFIC_NAME='{scientific_name}'",
        'outFields': ",".join(out_fields),
        'returnGeometry': 'false',
        'f': 'json'
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None
if __name__ == "__main__":
    main()
    st.markdown('<hr style="margin-top:2em;margin-bottom:0.5em;">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; color:gray; font-size:0.95em;">✨ Developed by Awesome People ✨</div>', unsafe_allow_html=True)
