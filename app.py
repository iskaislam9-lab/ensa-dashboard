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
    st.warning("Aucune réponse pour le moment.")
else:
    st.write("Nombre de colonnes:", len(df.columns))
    st.write("Noms des colonnes:", df.columns.tolist())