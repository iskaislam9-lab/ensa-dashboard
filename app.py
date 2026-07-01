import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image

st.set_page_config(page_title="Dashboard ENSA Agadir", layout="wide")

try:
    logo = Image.open("logo.png")
    st.image(logo, width=200)
except:
    pass

st.title("ENSA Agadir — Tableau de bord des tendances de carrière")
st.write("Bienvenue sur le dashboard des étudiants de l'ENSA Agadir.")

@st.cache_data(ttl=600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key("1khAfXgb6PQQz16xk4HkXG4wHr_5o2YscR6oHdK-urJg").sheet1
    return pd.DataFrame(sheet.get_all_records())

df = load_data()

if df.empty:
    st.warning("Aucune réponse pour le moment. Partagez le formulaire pour collecter des données.")
else:
    df = df.fillna("Non spécifié")
    df = df.replace("", "Non spécifié")
    df.columns = [str(c).strip() for c in df.columns]
    col = df.columns.tolist()

    # Sidebar filters
    st.sidebar.header("Filtres")
    années = ["Toutes"] + sorted(df[col[1]].unique().tolist())
    filtre_année = st.sidebar.selectbox("Filtrer par année d'études", années)
    if filtre_année != "Toutes":
        df = df[df[col[1]] == filtre_année]

    st.metric("Total des réponses", len(df))

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Télécharger les données en CSV",
        data=csv,
        file_name="ensa_responses.csv",
        mime="text/csv"
    )

    # --- STATISTIQUES GLOBALES ---
    st.header("Statistiques Globales")

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Répartition par année d'études")
        st.bar_chart(df[col[1]].value_counts())
    with c2:
        st.subheader("Ambition professionnelle claire ?")
        st.bar_chart(df[col[2]].value_counts())

    st.subheader("Filière de baccalauréat")
    st.bar_chart(df[col[3]].value_counts())

    # --- CYCLE PRÉPARATOIRE ---
    prepas = df[df[col[1]].isin(["AP1", "AP2"])]
    if not prepas.empty:
        st.header("Focus : Cycle Préparatoire (AP)")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1er choix de filière")
            st.bar_chart(prepas[col[4]].value_counts())
        with c2:
            st.subheader("2ème choix de filière")
            st.bar_chart(prepas[col[5]].value_counts())

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Facteur principal du choix")
            st.bar_chart(prepas[col[6]].value_counts())
        with c2:
            st.subheader("Craintes concernant la future filière")
            st.bar_chart(prepas[col[9]].value_counts())

    # --- CYCLE INGÉNIEUR ---
    ci = df[df[col[1]] == "CI1"]
    if not ci.empty:
        st.header("Focus : Cycle Ingénieur (CI)")

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Filière actuelle")
            st.bar_chart(ci[col[11]].value_counts())
        with c2:
            st.subheader("Cette filière était-elle le 1er choix ?")
            st.bar_chart(ci[col[12]].value_counts())

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Objectif de carrière après diplôme")
            st.bar_chart(ci[col[17]].value_counts())
        with c2:
            st.subheader("Logiciels et outils à jour ?")
            st.bar_chart(ci[col[16]].value_counts())

        st.subheader("Raison si attentes non comblées")
        st.bar_chart(ci[col[14]].value_counts())