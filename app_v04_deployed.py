import pandas as pd
import streamlit as st
import re

# ------------------------------------
# Configuration
# ------------------------------------
GOOGLE_DRIVE_FILE_ID = "1sqJN3HNnBOkvCMbnnTrKXE3nMBZ_E4Ke"
CSV_URL = f"https://drive.google.com/uc?export=download&id={GOOGLE_DRIVE_FILE_ID}"

st.set_page_config(page_title="ORTQAI.bibliothèque", layout="wide")
st.title("Bibliothèque de l'ORTQAI")
st.write("Recherche, sélection et filtre de documents")

# ------------------------------------
# Load data
# ------------------------------------
@st.cache_data
def load_data(url):
    return pd.read_csv(url)

df = load_data(CSV_URL)
df.columns = df.columns.str.strip()

# ------------------------------------
# Extract keywords
# ------------------------------------
keyword_columns = [c for c in df.columns if c.startswith("Sélectionnez cinq mots clés")]

def extract_keywords(row):
    kws = []
    for col in keyword_columns:
        if str(row[col]).strip().lower() == "oui":
            match = re.search(r"\[(.*?)\]", col)
            if match:
                kws.append(match.group(1))
    return ", ".join(kws)

df["Key-words"] = df.apply(extract_keywords, axis=1)

# ------------------------------------
# Columns selection
# ------------------------------------
link_column = "Lien URL vers le document."
cols_to_show = [
    "Type de document",
    "Titre du document.",
    "Auteur(s) (Nom, Prénom), séparer les auteurs par ;.",
    "Année de publication",
    "Brève description de l'ouvrage. Idéalement, il s'agit de résumer, dans ses grandes lignes, le contenu de l'ouvrage.",
    "Langue du document.",
    "Key-words",
    link_column
]

df_display = df[cols_to_show].copy()

df_display = df_display.rename(columns={
    "Type de document": "Type",
    "Titre du document.": "Titre",
    "Auteur(s) (Nom, Prénom), séparer les auteurs par ;.": "Auteur(s)",
    "Année de publication": "Année",
    "Brève description de l'ouvrage. Idéalement, il s'agit de résumer, dans ses grandes lignes, le contenu de l'ouvrage.": "Résumé",
    "Langue du document.": "Langue",
    "Key-words": "Mots-clés",
    link_column: "Lien"
})

# ------------------------------------
# Sidebar filters
# ------------------------------------
st.sidebar.header("Filtres")

for key in ["types", "langs", "keywords", "search"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key != "search" else ""

if st.sidebar.button("Réinitialiser tous les filtres"):
    st.session_state.types = []
    st.session_state.langs = []
    st.session_state.keywords = []
    st.session_state.search = ""

st.session_state.types = st.sidebar.multiselect(
    "Type de document",
    sorted(df_display["Type"].dropna().unique())
)

st.session_state.langs = st.sidebar.multiselect(
    "Langue",
    sorted(df_display["Langue"].dropna().unique())
)

all_keywords = sorted({
    k.strip()
    for row in df_display["Mots-clés"].dropna()
    for k in row.split(",")
    if k.strip()
})

st.session_state.keywords = st.sidebar.multiselect(
    "Mots-clés",
    all_keywords
)

st.session_state.search = st.sidebar.text_input("Recherche générale")

# ------------------------------------
# Apply filters
# ------------------------------------
filtered_df = df_display.copy()

if st.session_state.types:
    filtered_df = filtered_df[filtered_df["Type"].isin(st.session_state.types)]

if st.session_state.langs:
    filtered_df = filtered_df[filtered_df["Langue"].isin(st.session_state.langs)]

if st.session_state.keywords:
    filtered_df = filtered_df[
        filtered_df["Mots-clés"].apply(
            lambda x: all(k in [i.strip() for i in x.split(",")] for k in st.session_state.keywords)
        )
    ]

if st.session_state.search:
    filtered_df = filtered_df[
        filtered_df.astype(str).apply(
            lambda row: row.str.contains(st.session_state.search, case=False).any(), axis=1
        )
    ]

# ------------------------------------
# Styling
# ------------------------------------
pd.set_option("display.max_colwidth", None)

def style_table(df):
    styles = pd.DataFrame("", index=df.index, columns=df.columns)

    for i in df.index:
        styles.loc[i, :] = (
            "background-color: #fafafa;" if i % 2 == 0 else "background-color: white;"
        )

        if st.session_state.keywords:
            styles.loc[i, "Mots-clés"] = "background-color: #fff4b0;"

    return styles

# ------------------------------------
# Display table
# ------------------------------------
st.write(f"### Résultats ({len(filtered_df)})")

st.dataframe(
    filtered_df.style
    .apply(lambda _: style_table(filtered_df), axis=None)
    .set_properties(**{
        "white-space": "pre-wrap",
        "word-wrap": "break-word"
    }),
    use_container_width=True,
    column_config={
        "Type": st.column_config.TextColumn(width="small"),
        "Année": st.column_config.TextColumn(width="small"),
        "Langue": st.column_config.TextColumn(width="small"),
        "Auteur(s)": st.column_config.TextColumn(width="medium"),
        "Titre": st.column_config.TextColumn(width="medium"),
        "Mots-clés": st.column_config.TextColumn(width="medium"),
        "Résumé": st.column_config.TextColumn(width="large"),
        "Lien": st.column_config.LinkColumn("Document", display_text="Ouvrir")
    }
)
