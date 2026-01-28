import pandas as pd
import streamlit as st
import re

# ------------------------------------
# Configuration
# ------------------------------------
GOOGLE_DRIVE_FILE_ID = "1sqJN3HNnBOkvCMbnnTrKXE3nMBZ_E4Ke"  # Update your file ID
FILE_TYPE = "csv"  # "csv" or "xlsx"

st.set_page_config(page_title="ORTQAI.bibliothèque", layout="wide")
st.title("Bibliothèque de l'ORTQAI")
st.write("Recherche, sélection et filtre de documents")

# ------------------------------------
# Load data
# ------------------------------------
@st.cache_data(show_spinner="Chargement des données…")
def load_drive_file(file_id: str, file_type: str = "csv") -> pd.DataFrame:
    url = f"https://drive.google.com/uc?export=download&id={file_id}"
    try:
        if file_type == "csv":
            return pd.read_csv(url, sep=None, engine="python", encoding="utf-8")
        elif file_type == "xlsx":
            import openpyxl
            return pd.read_excel(url, engine="openpyxl")
        else:
            raise ValueError("file_type must be 'csv' or 'xlsx'")
    except Exception as e:
        st.error("Impossible de lire le fichier depuis Google Drive.")
        st.exception(e)
        return pd.DataFrame()

df = load_drive_file(GOOGLE_DRIVE_FILE_ID, FILE_TYPE)
if df.empty:
    st.stop()

# ------------------------------------
# Clean column names
# ------------------------------------
df.columns = df.columns.str.strip()

# ------------------------------------
# Extract keywords
# ------------------------------------
keyword_columns = [c for c in df.columns if c.startswith("Sélectionnez cinq mots clés")]

def extract_keywords(row):
    keywords = []
    for col in keyword_columns:
        value = str(row.get(col, "")).strip().lower()
        if value == "oui":
            match = re.search(r"\[(.*?)\]", col)
            if match:
                keywords.append(match.group(1))
    return ", ".join(sorted(set(keywords)))

df["Mots-clés"] = df.apply(extract_keywords, axis=1)

# ------------------------------------
# Assign correct URL column
# ------------------------------------
url_column = "Lien URL vers le document."
df["Lien"] = df[url_column]

# ------------------------------------
# Columns to display
# ------------------------------------
cols_to_show = [
    "Type de document",
    "Titre du document.",
    "Auteur(s) (Nom, Prénom), séparer les auteurs par ;.",
    "Année de publication",
    "Brève description de l'ouvrage. Idéalement, il s'agit de résumer, dans ses grandes lignes, le contenu de l'ouvrage.",
    "Langue du document.",
    "Mots-clés",
    "Lien"
]

df_display = df[cols_to_show].copy()
df_display = df_display.loc[:, ~df_display.columns.duplicated()]

# ------------------------------------
# Rename columns
# ------------------------------------
df_display = df_display.rename(columns={
    "Type de document": "Type de document",
    "Titre du document.": "Titre",
    "Auteur(s) (Nom, Prénom), séparer les auteurs par ;.": "Auteur(s)",
    "Année de publication": "Année de publication",
    "Brève description de l'ouvrage. Idéalement, il s'agit de résumer, dans ses grandes lignes, le contenu de l'ouvrage.": "Résumé",
    "Langue du document.": "Langue"
})

# Ensure Mots-clés exists
if "Mots-clés" not in df_display.columns:
    df_display["Mots-clés"] = ""

# ------------------------------------
# Sidebar filters
# ------------------------------------
st.sidebar.header("Filtres")

# Initialize session_state for filters
defaults = {
    "selected_types": [],
    "selected_langs": [],
    "selected_keywords": [],
    "search_text": ""
}

for key, default in defaults.items():
    st.session_state.setdefault(key, default)

# Reset button
if st.sidebar.button("🔄 Réinitialiser tous les filtres"):
    for key in defaults:
        st.session_state[key] = []
    st.rerun()

# Multi-selects
selected_types = st.sidebar.multiselect(
    "Type de document",
    sorted(df_display["Type de document"].dropna().unique()),
    default=st.session_state.selected_types,
    key="selected_types"
)

selected_langs = st.sidebar.multiselect(
    "Langue",
    sorted(df_display["Langue"].dropna().unique()),
    default=st.session_state.selected_langs,
    key="selected_langs"
)

all_keywords = sorted({
    kw.strip()
    for row in df_display["Mots-clés"].dropna()
    for kw in row.split(",")
    if kw.strip()
})

selected_keywords = st.sidebar.multiselect(
    "Mots-clés",
    all_keywords,
    default=st.session_state.selected_keywords,
    key="selected_keywords"
)

# Global search
search_text = st.sidebar.text_input(
    "Recherche générale",
    value=st.session_state.search_text,
    key="search_text"
)

# ------------------------------------
# Apply filters
# ------------------------------------
filtered_df = df_display.copy()

if selected_types:
    filtered_df = filtered_df[filtered_df["Type de document"].isin(selected_types)]

if selected_langs:
    filtered_df = filtered_df[filtered_df["Langue"].isin(selected_langs)]

if selected_keywords:
    filtered_df = filtered_df[
        filtered_df["Mots-clés"].apply(
            lambda x: all(kw in [i.strip() for i in x.split(",")] for kw in selected_keywords)
        )
    ]

if search_text:
    filtered_df = filtered_df[
        filtered_df.astype(str).apply(lambda row: row.str.contains(search_text, case=False, na=False).any(), axis=1)
    ]

# ------------------------------------
# Make links clickable in new tab
# ------------------------------------
filtered_df["Lien"] = filtered_df["Lien"].apply(
    lambda x: f'<a href="{x}" target="_blank">Ouvrir</a>' if pd.notna(x) and x else ""
)

# ------------------------------------
# Display results
# ------------------------------------
st.write(f"### Résultats ({len(filtered_df)})")
st.markdown(
    filtered_df.to_html(escape=False, index=False),
    unsafe_allow_html=True
)
