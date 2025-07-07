# Plant Species Identifier with Pl@ntNet API


This Streamlit app lets you identify plant species from an image using the Pl@ntNet API. It displays possible matches in an interactive table, and you can select a species to view detailed information from Wikipedia, including summary, description, invasive status, and toxicity (with highlighted warnings).

## Features
- Upload a plant image (jpg, jpeg, png)
- Select the plant organ (leaf, flower, fruit, bark, habit, auto)
- View results in an interactive table (AgGrid)
- Select a species to view Wikipedia info, including:
  - Title, summary, and description
  - Invasive species and toxicity sections (if available)
  - Toxicity warnings are highlighted and expandable

## Setup
1. **Clone the repository**
2. **Install dependencies**
   ```sh
   pip install -r requirements.txt
   ```
3. **Get a Pl@ntNet API key**
   - Register at [Pl@ntNet API](https://my.plantnet.org/)
   - Add your key to a `.env` file:
     ```
     PLANTNET_API_KEY=your_actual_api_key_here
     ```
4. **Run the app**
   ```sh
   streamlit run app.py
   ```

## Usage
- Upload a plant image using the sidebar.
- Select the organ type.
- View the results table. Select a species from the dropdown to see its Wikipedia details.
- Invasive species and toxicity info (if available) are shown below the summary.

## Requirements
- Python 3.7+
- See `requirements.txt` for all dependencies.

## Notes
- Your IP must be allowed by Pl@ntNet API. See their documentation if you get a 403 error.
- This app uses [streamlit-aggrid](https://github.com/PablocFonseca/streamlit-aggrid) for interactive tables.
- Wikipedia logic is modularized in `wikipedia_utils.py` for maintainability.

## License
MIT
