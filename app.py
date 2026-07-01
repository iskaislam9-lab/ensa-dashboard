import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
st.set_page_config(page_title="Dashboard ENSA Agadir", layout="wide")

# Helper for caching
@st.cache_resource
def get_gspread_client():
    creds_dict = st.secrets["gcp_service_account"]
    scope = ["https://spreadsheets.google.com/feeds", "https://spreadsheets.google.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    return gspread.authorize(creds)

@st.cache_data(ttl=600)
def fetch_data():
    client = get_gspread_client()
    sheet = client.open_by_key("1khAfXgb6PQQz16xk4HkXG4wHr_5o2YscR6oHdK-urJg").sheet1
    df = pd.DataFrame(sheet.get_all_records())
    
    # Map raw columns to readable names
    column_mapping = {
        "Niveau": "Niveau", "Ambition": "Ambition", "Bac": "Bac", 
        "Choix1": "Choix 1", "Choix2": "Choix 2", "Facteur": "Facteur", 
        "Comprehension": "Compréhension", "Orientation": "Orientation", 
        "Crainte": "Crainte", "Filiere_CI": "Filière CI", "Premier_Choix": "1er Choix ?", 
        "Correspondance": "Correspondance", "Raison": "Raison", "Objectif": "Objectif", 
        "SoftSkills": "Soft Skills", "Projets": "Projets"
    }
    df = df.rename(columns=column_mapping)
    return df.fillna("Non spécifié")

# --- UI LOGIC ---
st.title("📊 Dashboard ENSA Agadir")

df = fetch_data()

# Sidebar Filters
st.sidebar.header("Filtres")
niveau_filter = st.sidebar.multiselect("Filtrer par niveau", options=df["Niveau"].unique(), default=df["Niveau"].unique())
df_filtered = df[df["Niveau"].isin(niveau_filter)]

# Dashboard Metrics
col1, col2, col3 = st.columns(3)
col1.metric("Total Réponses", len(df_filtered))
col2.metric("Niveaux Actifs", len(niveau_filter))

# Function for clean charting
def display_chart(data, column, title):
    st.subheader(title)
    st.bar_chart(data[column].value_counts())

# Tabbed Layout
tab1, tab2 = st.tabs(["📈 Statistiques Globales", "🎓 Focus Cycles"])

with tab1:
    c1, c2 = st.columns(2)
    with c1: display_chart(df_filtered, "Niveau", "Répartition par niveau")
    with c2: display_chart(df_filtered, "Ambition", "Ambition professionnelle")

with tab2:
    # Logic for dynamically showing tabs based on filter
    if "AP1" in niveau_filter or "AP2" in niveau_filter:
        st.subheader("Cycle Préparatoire")
        c1, c2 = st.columns(2)
        with c1: display_chart(df_filtered[df_filtered["Niveau"].isin(["AP1", "AP2"])], "Choix 1", "1er Choix Filière")
        with c2: display_chart(df_filtered[df_filtered["Niveau"].isin(["AP1", "AP2"])], "Crainte", "Craintes principales")

    if "CI1" in niveau_filter:
        st.subheader("Cycle Ingénieur")
        c1, c2 = st.columns(2)
        with c1: display_chart(df_filtered[df_filtered["Niveau"] == "CI1"], "Filière CI", "Répartition Filières")
        with c2: display_chart(df_filtered[df_filtered["Niveau"] == "CI1"], "Correspondance", "Correspondance Attentes")

# Footer / Download
st.divider()
csv = df_filtered.to_csv(index=False).encode("utf-8")
st.download_button("📥 Télécharger les données filtrées", csv, "ensa_data.csv", "text/csv")