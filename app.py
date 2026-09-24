import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from PIL import Image

st.set_page_config(page_title="Dashboard ENSA Agadir", layout="wide")

SHEET_ID = "1khAfXgb6PQQz16xk4HkXG4wHr_5o2YscR6oHdK-urJg"

# Map the REAL Google Form question text (as it appears as a column header
# in the Sheet) to a short internal name used everywhere else in this app.
# ⚠️ CHECK EVERY LINE against your actual Sheet header row before running —
# a mismatched key just gets silently dropped (see clean_data's warning below).
COLUMN_MAP = {
    "Horodateur": "Timestamp",
    "Année d'études :": "Niveau",
    "Avez-vous déjà une ambition professionnelle claire?": "Ambition",
    "Quelle est votre filière de baccalauréat ?": "Bac",

    # --- Section Parcours Préparatoire (AP1/AP2) ---
    "Si vous deviez choisir votre filière aujourd'hui, quelle serait votre 1er choix ?": "Choix1",
    "Quel serait votre 2e choix ?": "Choix2",
    "Quel est le facteur principal qui influence votre 1er choix ?": "Facteur",
    "Sur une échelle de 1 à 5, dans quelle mesure comprenez-vous le contenu et les modules de votre 1er choix ?": "Comprehension",
    "Estimez-vous que l'ENSA d'Agadir fournit assez d'informations pour vous aider à choisir ?": "Orientation",
    "Quelle est votre plus grande crainte concernant votre future filière ?": "Crainte",
    "Avez-vous déjà regardé des offres de stage ou des descriptions de postes liées à votre 1er choix de filière ?": "Stages_Regardes",
    "Si oui, quelle compétence vous semble la plus difficile à apprendre par vous-même ?": "Competence_Difficile",

    # --- Section Cycle Ingénieur (CI1/CI2/CI3) ---
    "Quelle est votre filière actuelle ?": "Filiere_CI",
    "Cette filière était-elle votre 1er choix lors de votre année en AP2 ?": "Premier_Choix",
    "Sur une échelle de 1 à 5, la réalité de cette filière correspond-elle aux attentes que vous aviez en AP2?": "Correspondance",
    "Si les attentes ne sont pas comblées, quelle en est la raison principale ?": "Raison",
    "Estimez-vous que les logiciels et outils enseignés sont à jour par rapport au marché du travail actuel ?": "Outils",
    "Quelle compétence technique, logiciel ou technologie souhaiteriez-vous voir intégrer ou approfondir dans votre filière ?": "Competence",
    "Quel est votre objectif de carrière principal après l'obtention de votre diplôme ?": "Objectif",
    "Comment évaluez-vous la formation aux \"soft skills\" (communication, gestion, leadership) au sein de votre filière ?": "SoftSkills",
    "Si vous deviez noter la pertinence des projets pratiques réalisés en cours par rapport aux besoins réels d'une entreprise, quelle note donneriez-vous (1-5) ?": "Projets",
    "Quel est le facteur principal qui a influencé votre choix de filière ?": "Facteur_CI",
    "Si vous pouviez revenir en AP2, referiez-vous le même choix de filière ?": "Regret",
}

TEXT_COLUMNS = ["Raison", "SoftSkills", "Projets", "Competence", "Competence_Difficile"]

# Questions where 5 = best outcome (understanding, orientation, expectations met,
# soft skills quality, project relevance) — used to sanity-check scale direction.
SCALE_5_IS_BEST = ["Comprehension", "Correspondance", "SoftSkills", "Projets"]

CI_LEVELS = ["CI1", "CI2", "CI3"]
AP_LEVELS = ["AP1", "AP2"]


# ---------------------------------------------------------------------------
# DATA LOADING & CLEANING
# ---------------------------------------------------------------------------

@st.cache_data(ttl=600)
def load_data():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["gcp_service_account"]
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(creds_dict), scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1

    # Read raw values instead of get_all_records(): get_all_records() raises
    # if the header row has blank or duplicate cells, which happens easily
    # with a branching Google Form (e.g. two sections reusing similar wording).
    values = sheet.get_all_values()
    if len(values) < 2:
        return pd.DataFrame()

    headers = values[0]
    rows = values[1:]

    # De-duplicate / fill blank headers so pandas doesn't collapse columns
    seen = {}
    clean_headers = []
    for h in headers:
        h = h.strip() if h.strip() else "Colonne_vide"
        if h in seen:
            seen[h] += 1
            h = f"{h}_{seen[h]}"
        else:
            seen[h] = 0
        clean_headers.append(h)

    df = pd.DataFrame(rows, columns=clean_headers)
    return clean_data(df)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """Rename real Sheet headers to internal names, then normalize values."""
    df = df.copy()

    # Rename by matching real header text — anything not in COLUMN_MAP is left
    # as-is (so a form edit you forgot to add here shows up under its raw
    # question text instead of silently vanishing).
    unmapped = [c for c in df.columns if c not in COLUMN_MAP]
    if unmapped:
        st.sidebar.warning(
            "Colonnes non reconnues (à ajouter dans COLUMN_MAP) :\n- "
            + "\n- ".join(unmapped)
        )
    df = df.rename(columns=COLUMN_MAP)

    # Strip whitespace on every text column
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()

    if "Niveau" in df.columns:
        df["Niveau"] = df["Niveau"].str.upper()
    if "Filiere_CI" in df.columns:
        df["Filiere_CI"] = df["Filiere_CI"].str.upper()

    df = df.replace(r"^\s*$", "Non spécifié", regex=True)
    df = df.replace("NAN", "Non spécifié")
    df = df.fillna("Non spécifié")

    return df


def try_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce")


# ---------------------------------------------------------------------------
# UI SECTIONS
# ---------------------------------------------------------------------------

def render_header():
    try:
        logo = Image.open("logo.png")
        st.image(logo, width=200)
    except Exception:
        pass
    st.title("ENSA Agadir — Tableau de bord des tendances de carrière")
    st.write("Bienvenue sur le dashboard des étudiants de l'ENSA Agadir.")


def render_sidebar(df: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtres")

    annees = ["Toutes"] + sorted(df["Niveau"].unique().tolist())
    filtre_annee = st.sidebar.selectbox("Filtrer par année d'études", annees)
    if filtre_annee != "Toutes":
        df = df[df["Niveau"] == filtre_annee]

    if "Filiere_CI" in df.columns:
        filieres = ["Toutes"] + sorted(
            [f for f in df["Filiere_CI"].unique().tolist() if f != "Non spécifié"]
        )
        filtre_filiere = st.sidebar.selectbox("Filtrer par filière (CI)", filieres)
        if filtre_filiere != "Toutes":
            df = df[df["Filiere_CI"] == filtre_filiere]

    st.sidebar.header("Recherche par mot-clé")
    keyword = st.sidebar.text_input("Chercher dans Raison / SoftSkills / Projets / Compétence")
    if keyword:
        mask = pd.Series(False, index=df.index)
        for col in TEXT_COLUMNS:
            if col in df.columns:
                mask = mask | df[col].str.contains(keyword, case=False, na=False)
        df = df[mask]
        st.sidebar.caption(f"{len(df)} réponse(s) contenant « {keyword} »")

    return df


def render_kpis(df: pd.DataFrame):
    st.header("Indicateurs Clés")
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("Total des réponses", len(df))

    with c2:
        comp_numeric = try_numeric(df.get("Comprehension", pd.Series(dtype=object)))
        avg_comp = comp_numeric.mean()
        st.metric(
            "Compréhension moyenne",
            f"{avg_comp:.1f}" if pd.notna(avg_comp) else "N/A"
        )

    with c3:
        ci = df[df["Niveau"].isin(CI_LEVELS)]
        if not ci.empty and "Premier_Choix" in ci.columns:
            oui = ci["Premier_Choix"].str.lower().str.startswith("oui").sum()
            pct = 100 * oui / len(ci)
            st.metric("1er choix obtenu (CI)", f"{pct:.0f}%")
        else:
            st.metric("1er choix obtenu (CI)", "N/A")

    with c4:
        corr_numeric = try_numeric(df.get("Correspondance", pd.Series(dtype=object)))
        avg_corr = corr_numeric.mean()
        if pd.notna(avg_corr):
            st.metric("Indice de satisfaction", f"{avg_corr:.1f} / 5")
        else:
            corr = df.get("Correspondance", pd.Series(dtype=object))
            oui = corr.str.lower().str.contains("oui", na=False).sum()
            pct = 100 * oui / len(df) if len(df) else 0
            st.metric("Indice de satisfaction", f"{pct:.0f}%")


def bar(df_counts, title, x_label, y_label="Nombre de réponses"):
    fig = px.bar(
        df_counts, x=df_counts.index, y=df_counts.values,
        labels={"x": x_label, "y": y_label}, title=title
    )
    fig.update_layout(showlegend=False, xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)


def render_global_stats(df: pd.DataFrame):
    st.header("Statistiques Globales")

    c1, c2 = st.columns(2)
    with c1:
        bar(df["Niveau"].value_counts(), "Répartition par année d'études", "Niveau")
    with c2:
        bar(df["Ambition"].value_counts(), "Ambition professionnelle claire ?", "Ambition")

    bar(df["Bac"].value_counts(), "Filière de baccalauréat", "Bac")


def render_prepa_section(df: pd.DataFrame):
    prepas = df[df["Niveau"].isin(AP_LEVELS)]
    if prepas.empty:
        return

    st.header("Focus : Cycle Préparatoire (AP)")

    c1, c2 = st.columns(2)
    with c1:
        bar(prepas["Choix1"].value_counts(), "1er choix de filière", "Filière")
    with c2:
        bar(prepas["Choix2"].value_counts(), "2ème choix de filière", "Filière")

    c1, c2 = st.columns(2)
    with c1:
        bar(prepas["Facteur"].value_counts(), "Facteur principal du choix", "Facteur")
    with c2:
        bar(prepas["Crainte"].value_counts(), "Craintes concernant la future filière", "Crainte")

    if "Stages_Regardes" in prepas.columns:
        bar(prepas["Stages_Regardes"].value_counts(), "Ont déjà regardé des offres de stage ?", "Réponse")


def render_ci_section(df: pd.DataFrame):
    ci = df[df["Niveau"].isin(CI_LEVELS)]
    if ci.empty:
        return

    st.header("Focus : Cycle Ingénieur (CI1/CI2/CI3)")

    c1, c2 = st.columns(2)
    with c1:
        bar(ci["Filiere_CI"].value_counts(), "Filière actuelle", "Filière")
    with c2:
        bar(ci["Premier_Choix"].value_counts(), "Cette filière était-elle le 1er choix ?", "Réponse")

    c1, c2 = st.columns(2)
    with c1:
        bar(ci["Objectif"].value_counts(), "Objectif de carrière après diplôme", "Objectif")
    with c2:
        bar(ci["Outils"].value_counts(), "Logiciels et outils à jour ?", "Réponse")

    if "Regret" in ci.columns:
        bar(ci["Regret"].value_counts(), "Referaient le même choix ?", "Réponse")

    bar(ci["Raison"].value_counts(), "Raison si attentes non comblées", "Raison")


def render_comparative_analysis(df: pd.DataFrame):
    """Crainte vs Correspondance: do students who feared certain aspects end up less satisfied?"""
    if "Crainte" not in df.columns or "Correspondance" not in df.columns:
        return
    subset = df[(df["Crainte"] != "Non spécifié") & (df["Correspondance"] != "Non spécifié")]
    if subset.empty:
        return

    st.header("Analyse Comparative : Craintes vs Satisfaction")
    cross = pd.crosstab(subset["Crainte"], subset["Correspondance"])
    fig = px.bar(
        cross, barmode="group",
        labels={"value": "Nombre de réponses", "Crainte": "Crainte initiale"},
        title="Correspondance aux attentes, par crainte initiale"
    )
    fig.update_layout(xaxis_tickangle=-30)
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Ce graphique révèle si les étudiants ayant exprimé une crainte particulière "
        "ont ensuite déclaré une satisfaction plus faible."
    )


def render_sankey(df: pd.DataFrame):
    """Bac -> Filiere_CI flow diagram."""
    ci = df[df["Niveau"].isin(CI_LEVELS) & (df["Bac"] != "Non spécifié") & (df["Filiere_CI"] != "Non spécifié")]
    if ci.empty:
        return

    st.header("Parcours Bac → Filière d'ingénieur")

    bacs = sorted(ci["Bac"].unique())
    filieres = sorted(ci["Filiere_CI"].unique())
    labels = bacs + filieres
    bac_idx = {b: i for i, b in enumerate(bacs)}
    fil_idx = {f: i + len(bacs) for i, f in enumerate(filieres)}

    flow = ci.groupby(["Bac", "Filiere_CI"]).size().reset_index(name="count")
    sources = flow["Bac"].map(bac_idx)
    targets = flow["Filiere_CI"].map(fil_idx)
    values = flow["count"]

    fig = go.Figure(data=[go.Sankey(
        node=dict(pad=15, thickness=15, label=labels),
        link=dict(source=sources, target=targets, value=values)
    )])
    fig.update_layout(title_text="Flux des étudiants : Bac d'origine → Filière actuelle", height=500)
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Répond à la question : les étudiants d'un Bac donné se dirigent-ils vers une filière spécifique ?")


def render_persona(df: pd.DataFrame):
    st.header("Profil Type d'un Étudiant")

    c1, c2 = st.columns(2)
    with c1:
        niveau = st.selectbox("Niveau", sorted(df["Niveau"].unique().tolist()), key="persona_niveau")
    subset = df[df["Niveau"] == niveau]

    filiere = None
    if niveau in CI_LEVELS and "Filiere_CI" in df.columns:
        options = sorted([f for f in subset["Filiere_CI"].unique() if f != "Non spécifié"])
        if options:
            with c2:
                filiere = st.selectbox("Filière", options, key="persona_filiere")
            subset = subset[subset["Filiere_CI"] == filiere]

    if subset.empty:
        st.info("Aucune donnée pour ce profil.")
        return

    def mode_or_na(col):
        if col not in subset.columns:
            return "N/A"
        vals = subset[col][subset[col] != "Non spécifié"]
        return vals.mode().iloc[0] if not vals.empty else "N/A"

    label = f"{niveau}" + (f" — {filiere}" if filiere else "")
    st.markdown(f"**Profil type : {label}** *(n={len(subset)})*")

    if niveau in CI_LEVELS:
        st.write(f"- Objectif de carrière le plus fréquent : **{mode_or_na('Objectif')}**")
        st.write(f"- Correspondance typique aux attentes : **{mode_or_na('Correspondance')}**")
        st.write(f"- Outils/compétences : **{mode_or_na('Outils')}**")
    else:
        st.write(f"- 1er choix de filière le plus fréquent : **{mode_or_na('Choix1')}**")
        st.write(f"- Facteur principal du choix : **{mode_or_na('Facteur')}**")
        st.write(f"- Crainte la plus fréquente : **{mode_or_na('Crainte')}**")


def render_download(df: pd.DataFrame):
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="Télécharger les données en CSV",
        data=csv,
        file_name="ensa_responses.csv",
        mime="text/csv"
    )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    render_header()
    df = load_data()

    if df.empty:
        st.warning("Aucune réponse pour le moment. Partagez le formulaire pour collecter des données.")
        return

    df = render_sidebar(df)

    if df.empty:
        st.info("Aucune réponse ne correspond aux filtres sélectionnés.")
        return

    render_download(df)
    render_kpis(df)
    render_global_stats(df)
    render_prepa_section(df)
    render_ci_section(df)
    render_comparative_analysis(df)
    render_sankey(df)
    render_persona(df)


if __name__ == "__main__":
    main()