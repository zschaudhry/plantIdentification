import streamlit as st
import requests
import os
from dotenv import load_dotenv
import pandas as pd
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode

# Load environment variables from .env file
load_dotenv()

st.title("🌿 Plant Species Identifier 🌿")
st.write("📷 Upload a plant image to identify its species using the Pl@ntNet API.")

def get_api_key():
    api_key = os.getenv("PLANTNET_API_KEY")
    if not api_key:
        st.error("Pl@ntNet API key not found. Please set PLANTNET_API_KEY in your .env file.")
        return None
    return api_key

def identify_plant(image_file, organ, api_key):
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

def build_results_dataframe(results):
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

def show_aggrid(df):
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_selection('single', use_checkbox=False)
    grid_options = gb.build()
    grid_height = min(500, max(150, 35 * (len(df) + 1)))
    grid_response = AgGrid(
        df,
        gridOptions=grid_options,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        theme='streamlit',
        height=grid_height,
        fit_columns_on_grid_load=True,
        key="plant_grid"
    )
    return grid_response

def get_wikipedia_summary(scientific_name):
    wiki_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{scientific_name.replace(' ', '_')}"
    try:
        resp = requests.get(wiki_url)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.error(f"Wikipedia request failed: {e}")
    return None

def get_wikidata_taxonomy(wikidata_id):
    wikidata_url = f'https://www.wikidata.org/wiki/Special:EntityData/{wikidata_id}.json'
    try:
        wd_resp = requests.get(wikidata_url)
        if wd_resp.status_code != 200:
            return None
        wd_data = wd_resp.json()
        entity = wd_data['entities'].get(wikidata_id, {})
        claims = entity.get('claims', {})
        taxonomy_props = {
            'kingdom': 'P75',
            'phylum': 'P76',
            'class': 'P77',
            'order': 'P70',
            'family': 'P71',
            'genus': 'P74',
            'species': 'P225',
        }
        taxonomy = {}
        for rank, prop in taxonomy_props.items():
            if prop in claims:
                val = claims[prop][0]['mainsnak']['datavalue']['value']
                if isinstance(val, dict) and 'id' in val:
                    label_url = f'https://www.wikidata.org/wiki/Special:EntityData/{val["id"]}.json'
                    label_resp = requests.get(label_url)
                    if label_resp.status_code == 200:
                        label_data = label_resp.json()
                        label_entity = label_data['entities'].get(val['id'], {})
                        label = label_entity.get('labels', {}).get('en', {}).get('value', val['id'])
                        taxonomy[rank] = label
                    else:
                        taxonomy[rank] = val['id']
                else:
                    taxonomy[rank] = str(val)
        return taxonomy if taxonomy else None
    except Exception as e:
        st.info(f"Could not fetch taxonomy from Wikidata: {e}")
        return None

def main():
    uploaded_file = st.sidebar.file_uploader("Upload an image...", type=["jpg", "jpeg", "png"])
    if not uploaded_file:
        st.info("Please upload an image to begin.")
        return

    st.image(uploaded_file, caption="Uploaded Image", width=150)
    api_key = get_api_key()
    if not api_key:
        return

    organ_options = ["auto", "leaf", "flower", "fruit", "bark", "habit"]
    organ = st.selectbox("Select the organ shown in the image:", organ_options, index=0)
    with st.spinner("Identifying..."):
        result = identify_plant(uploaded_file, organ, api_key)
    if not result or 'results' not in result or not result['results']:
        st.warning("No species identified. Try another image.")
        return

    df = build_results_dataframe(result['results'])
    grid_response = show_aggrid(df)

    scientific_names = df['Scientific Name'].tolist() if 'Scientific Name' in df.columns else []
    if not scientific_names:
        st.warning("No scientific names found in results.")
        return

    selected_name = st.selectbox("Select a scientific name:", scientific_names, index=0)
    if not selected_name:
        st.info("Select a scientific name from the dropdown to see its details below.")
        return

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
        st.markdown(f"[🔗 Read more on Wikipedia]({wiki_data.get('content_urls', {}).get('desktop', {}).get('page', '')})")

if __name__ == "__main__":
    main()
    st.markdown('<hr style="margin-top:2em;margin-bottom:0.5em;">', unsafe_allow_html=True)
    st.markdown('<div style="text-align:center; color:gray; font-size:0.95em;">✨ Developed by Awesome People ✨</div>', unsafe_allow_html=True)
