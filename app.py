from pathlib import Path
import ast
import re

import pandas as pd
import plotly.express as px
import streamlit as st

# ------------------------------------------------------------
# IMDb TOP 250 MOVIES: STREAMLIT PRACTICAL EXAMINATION
# Section A: Dataset loading
# Section B: KPIs, charts, tabs and layout
# Section C: Interactive explorer, form and session state
# ------------------------------------------------------------

st.set_page_config(
    page_title="IMDb Movie Analytics Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

FOLDER = Path(__file__).parent

# The original CSV is not renamed or modified.
csv_files = sorted(FOLDER.glob("*.csv"))
# Use the expected IMDb dataset when other CSV files are in the folder.
preferred = [p for p in csv_files if "250" in p.name.lower() and "imdb" in p.name.lower()]
if preferred:
    csv_files = preferred + [p for p in csv_files if p not in preferred]
if not csv_files:
    st.error("Put your IMDb Top 250 Movies CSV file in the same folder as app.py.")
    st.stop()

@st.cache_data
def load_data(path):
    try:
        return pd.read_csv(path, encoding="utf-8-sig")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp1252")

try:
    raw_df = load_data(str(csv_files[0]))
except Exception as exc:
    st.error("Could not read the CSV. Confirm that the file is a valid CSV and committed to GitHub.")
    st.exception(exc)
    st.stop()

# Columns in the question paper are averageRating, numVotes, grossWorldwide.
# This also supports a few common CSV spelling variations.
def pick_column(*possible_names):
    existing = {re.sub(r"[^a-z0-9]", "", str(c).lower()): c for c in raw_df.columns}
    for name in possible_names:
        match = existing.get(re.sub(r"[^a-z0-9]", "", name.lower()))
        if match is not None:
            return match
    return None

column_names = {
    "Title": pick_column("primaryTitle", "title", "movieTitle", "movie"),
    "Genre": pick_column("genres", "genre"),
    "Country": pick_column("countriesOfOrigin", "countryOfOrigin", "country", "countries"),
    "IMDb Rating": pick_column("averageRating", "imdbRating", "rating"),
    "Votes": pick_column("numVotes", "votes"),
    "Worldwide Gross": pick_column("grossWorldwide", "worldwideGross", "gross"),
}

required = ["Title", "Genre", "Country", "IMDb Rating", "Votes", "Worldwide Gross"]
missing_columns = [name for name in required if column_names[name] is None]
if missing_columns:
    st.error(f"Missing required columns: {', '.join(missing_columns)}")
    st.write("Your CSV column names:", raw_df.columns.tolist())
    st.stop()

movies = raw_df.rename(columns={v: k for k, v in column_names.items()}).copy()

# Convert values such as "2,206,251", "$2.92B", and "$150M" to numbers.
def to_number(value):
    if pd.isna(value):
        return 0.0
    text = str(value).replace(",", "").replace("$", "").replace("₹", "").strip()
    if not text or text.lower() in {"none", "nan", "n/a", "unknown"}:
        return 0.0
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return 0.0
    number = float(match.group())
    suffix = text[match.end():].strip().lower()
    if suffix.startswith("b"):
        number *= 1_000_000_000
    elif suffix.startswith("m"):
        number *= 1_000_000
    elif suffix.startswith("k"):
        number *= 1_000
    return number

# Genres/countries may be comma-separated or stored as Python-style lists.
def split_values(value):
    if pd.isna(value):
        return []
    text = str(value).strip()
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
            if isinstance(parsed, (list, tuple, set)):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (ValueError, SyntaxError):
            pass
    return [item.strip().strip("'\"[]") for item in re.split(r"[,;|]", text) if item.strip().strip("'\"[]")]

movies["Title"] = movies["Title"].fillna("Unknown").astype(str)
movies["Genre"] = movies["Genre"].fillna("").astype(str)
movies["Country"] = movies["Country"].fillna("").astype(str)
movies["IMDb Rating"] = pd.to_numeric(
    movies["IMDb Rating"].astype(str).str.replace(",", "", regex=False),
    errors="coerce"
)
movies["Votes"] = movies["Votes"].apply(to_number).round().astype("int64")
movies["Worldwide Gross"] = movies["Worldwide Gross"].apply(to_number)

all_genres = sorted({item for entry in movies["Genre"] for item in split_values(entry)})
all_countries = sorted({item for entry in movies["Country"] for item in split_values(entry)})
ratings = movies["IMDb Rating"].dropna()
if ratings.empty:
    st.error("The dataset does not contain valid IMDb ratings.")
    st.stop()

# ------------------------------------------------------------
# DASHBOARD STYLING
# ------------------------------------------------------------
st.markdown("""
<style>
.stApp {background: linear-gradient(130deg, #111827, #1c293d); color: #f8fafc;}
[data-testid="stSidebar"] {background: linear-gradient(165deg,#202b3d,#141b29); border-right:1px solid #475569;}
[data-testid="stSidebar"] * {color:#f8fafc;}
.block-container {max-width:1800px; padding: .6rem 1rem 2rem;}
.imdb-logo {display:inline-block;background:#f5c518;color:#0b0b0b!important; padding:6px 13px;
 font-weight:950;font-size:36px;border-radius:9px;letter-spacing:-2px;}
.sidebar-title {font-size:23px;font-weight:800;line-height:1.25;margin:13px 0 16px;}
.kpi {border-radius:12px;color:white;min-height:87px;padding:15px;display:flex;
 align-items:center;gap:14px;box-shadow:0 3px 10px #0b1323;}
.kpi-icon {font-size:38px;}
.kpi-label {font-size:14px;font-weight:700;}
.kpi-value {font-size:29px;font-weight:850;}
.section-title {font-size:19px;font-weight:800; padding:8px 10px;
 background:linear-gradient(90deg,#303f62,#202d43);border-radius:8px;}
.chart-title {font-size:16px;font-weight:750;margin:5px 0 1px;color:#f8fafc;}
.stTabs [data-baseweb="tab-list"] {gap:10px;}
.stTabs [data-baseweb="tab"] {background:#28364e;border-radius:9px 9px 0 0;color:white;}
.stTabs [aria-selected="true"] {background:#2389eb!important;color:white!important;}
[data-testid="stExpander"] {background:#27344a;border-radius:9px;}
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button {
 background:#8355e7;color:white;border:none;}
[data-testid="stDataFrame"] {border-radius:8px;overflow:hidden;}
.side-heading {font-size:18px;font-weight:800;margin:12px 0;}
.student-note {background:#302a4d;border:1px solid #aa79f2;
 border-left:5px solid #aa79f2;border-radius:9px;padding:12px;
 font-size:13px;line-height:1.9;margin-top:28px;color:white;}
</style>
""", unsafe_allow_html=True)

# Sidebar: navigation and dataset information (st.expander).
with st.sidebar:
    st.markdown('<div class="imdb-logo">IMDb</div>', unsafe_allow_html=True)
    st.markdown('<div class="sidebar-title">Movie Analytics<br>Dashboard</div>', unsafe_allow_html=True)
    st.divider()
    page = st.radio(
        "Navigation",
        ["🏠 Dashboard", "🔎 Movie Explorer", "🔍 Movie Search (Form + Session State)"],
        label_visibility="collapsed",
    )
    st.divider()
    st.markdown('<div class="side-heading">ℹ️ Dataset Metadata</div>', unsafe_allow_html=True)
    st.write(f"📏 **Rows:** {raw_df.shape[0]}")
    st.write(f"📐 **Columns:** {raw_df.shape[1]}")
    with st.expander("🔎 Metadata & Missing Values"):
        st.write("**Column Names**", raw_df.columns.tolist())
        st.write("**Data Types**", raw_df.dtypes.astype(str))
        st.write("**Missing Values**", raw_df.isna().sum())
    st.divider()
    st.markdown('<div class="side-heading">🎓 Student Details</div>', unsafe_allow_html=True)
    st.write("👤 **Name:** sk safivulla")
    st.write("📌 **Exam:** Practical Examination")
    st.markdown("""<div class="student-note">📝 <b>Created by sk safivulla</b><br>
    <b>PRN:</b> 250200337<br><b>Date:</b>06/11/2026</div>""",
    unsafe_allow_html=True)

# Session state: preserve the selected movie between reruns.
if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None


def kpi_card(icon, label, value, background):
    st.markdown(
        f'<div class="kpi" style="background:{background}">'
        f'<div class="kpi-icon">{icon}</div>'
        f'<div><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div></div>',
        unsafe_allow_html=True,
    )


def chart_style(fig, height=265, left=15, right=15):
    # Dark text on white charts fixes invisible chart titles and axis labels.
    fig.update_layout(
        height=height,
        paper_bgcolor="#f5f8ff",
        plot_bgcolor="#f5f8ff",
        font=dict(color="#17253e", size=12),
        margin=dict(l=left, r=right, t=20, b=30),
        showlegend=False,
    )
    fig.update_xaxes(tickfont_color="#17253e", title_font_color="#17253e", gridcolor="#e2e9f3")
    fig.update_yaxes(tickfont_color="#17253e", title_font_color="#17253e", gridcolor="#e2e9f3")
    return fig


# Section B Question 3(a): number of movies by genre.
def genre_chart(key):
    genre_counts = movies["Genre"].apply(split_values).explode().dropna().value_counts().head(8)
    if genre_counts.empty:
        st.info("No genre information available.")
        return
    fig = px.bar(x=genre_counts.index, y=genre_counts.values, text=genre_counts.values,
                 labels={"x": "Genre", "y": "Count"})
    fig.update_traces(marker_color=["#2686d9", "#26b579", "#ffaf28", "#9545d6",
                                    "#2ba7df", "#e6a01e", "#4879e9", "#17a592"][:len(genre_counts)],
                      textposition="outside")
    st.plotly_chart(chart_style(fig), use_container_width=True, key=key,
                    config={"displayModeBar": False})


# Section B Question 3(b): histogram of IMDb ratings.
def rating_chart(key):
    fig = px.histogram(movies.dropna(subset=["IMDb Rating"]), x="IMDb Rating", nbins=15)
    fig.update_traces(marker_color="#2c85f6", marker_line_color="white", marker_line_width=1)
    fig.update_layout(xaxis_title="IMDb Rating", yaxis_title="Count")
    st.plotly_chart(chart_style(fig), use_container_width=True, key=key,
                    config={"displayModeBar": False})


# Section B Question 3(c): rating versus votes.
def votes_chart(key):
    fig = px.scatter(movies.dropna(subset=["IMDb Rating"]),
                     x="IMDb Rating", y="Votes", hover_name="Title")
    fig.update_traces(marker=dict(size=7, color="#248cf0", opacity=0.85))
    fig.update_layout(yaxis_title="Number of Votes", xaxis_title="IMDb Rating")
    st.plotly_chart(chart_style(fig), use_container_width=True, key=key,
                    config={"displayModeBar": False})


# Section B Question 3(d): top 10 by grossWorldwide.
def gross_chart(key):
    top10 = movies.sort_values("Worldwide Gross", ascending=False).head(10)
    top10 = top10.sort_values("Worldwide Gross")
    labels = top10["Worldwide Gross"].apply(
        lambda n: f"${n / 1e9:.2f}B" if n >= 1e9 else f"${n / 1e6:.0f}M"
    )
    fig = px.bar(top10, x="Worldwide Gross", y="Title", orientation="h", text=labels)
    fig.update_traces(marker_color="#ff921b", textposition="outside", cliponaxis=False)
    fig.update_layout(xaxis_title="Worldwide Gross (USD)", yaxis_title=None)
    fig.update_xaxes(tickformat="~s")
    st.plotly_chart(chart_style(fig, height=290, left=5, right=85),
                    use_container_width=True, key=key,
                    config={"displayModeBar": False})


def dashboard_charts():
    # Section B Question 4(a): st.tabs() organizes the charts.
    tab1, tab2, tab3 = st.tabs(["📊 Genre Analysis", "◕ Rating Analysis", "🪙 Gross Collection"])
    with tab1:
        a, b = st.columns(2)
        with a:
            st.markdown('<div class="chart-title">📊 Movies by Genre</div>', unsafe_allow_html=True)
            genre_chart("genre_main")
        with b:
            st.markdown('<div class="chart-title">📊 IMDb Rating Distribution</div>', unsafe_allow_html=True)
            rating_chart("rating_main")
        a, b = st.columns(2)
        with a:
            st.markdown('<div class="chart-title">💠 Rating vs Number of Votes</div>', unsafe_allow_html=True)
            votes_chart("votes_main")
        with b:
            st.markdown('<div class="chart-title">🏆 Top 10 Movies by Worldwide Gross</div>', unsafe_allow_html=True)
            gross_chart("gross_main")
    with tab2:
        a, b = st.columns(2)
        with a:
            st.subheader("IMDb Rating Distribution")
            rating_chart("rating_tab")  # Different key; avoids DuplicateElementId.
        with b:
            st.subheader("Rating vs Number of Votes")
            votes_chart("votes_tab")
    with tab3:
        st.subheader("Top 10 Movies by Worldwide Gross")
        gross_chart("gross_tab")


# Section C Question 5: filters + reset button.
def reset_filters():
    st.session_state["genre_filter"] = "All Genres"
    st.session_state["country_filter"] = []
    st.session_state["rating_filter"] = (0.0, 10.0)
    st.session_state["votes_filter"] = 0
    st.session_state["title_filter"] = ""
    st.session_state["sort_filter"] = "Descending"


def movie_explorer():
    st.markdown('<div class="section-title">🔎 Interactive Movie Explorer</div>', unsafe_allow_html=True)
    c1, c2, c3, c4, c5, c6 = st.columns([1.2, 1.3, 1.6, 1.1, 1.6, 1.2])
    with c1:
        genre = st.selectbox("Genre", ["All Genres"] + all_genres, key="genre_filter")
    with c2:
        countries = st.multiselect("Countries", all_countries, key="country_filter")
    with c3:
        rating_min, rating_max = st.slider("IMDb Rating", 0.0, 10.0,
                                           (0.0, 10.0), 0.1, key="rating_filter")
    with c4:
        minimum_votes = st.number_input("Min Votes", min_value=0, step=10000, key="votes_filter")
    with c5:
        title = st.text_input("Search Title", placeholder="Enter movie title...", key="title_filter")
    with c6:
        sort_order = st.radio("Sort Order", ["Ascending", "Descending"], index=1, key="sort_filter")

    filtered_df = movies.copy()
    if genre != "All Genres":
        filtered_df = filtered_df[filtered_df["Genre"].apply(lambda v: genre in split_values(v))]
    if countries:
        filtered_df = filtered_df[filtered_df["Country"].apply(
            lambda v: bool(set(countries).intersection(split_values(v))))]
    filtered_df = filtered_df[filtered_df["IMDb Rating"].between(rating_min, rating_max)]
    filtered_df = filtered_df[filtered_df["Votes"] >= minimum_votes]
    if title.strip():
        filtered_df = filtered_df[filtered_df["Title"].str.contains(
            title.strip(), case=False, na=False, regex=False)]
    filtered_df = filtered_df.sort_values("IMDb Rating", ascending=(sort_order == "Ascending"))

    a, b = st.columns([1.3, 5])
    with a:
        st.info(f"Filtered Movies: {len(filtered_df)}")
    with b:
        st.button("🔄 Reset Filters", on_click=reset_filters, key="reset_filters_button")

    visible = filtered_df[["Title", "Genre", "Country", "IMDb Rating", "Votes", "Worldwide Gross"]].copy()
    visible.insert(0, "#", range(1, len(visible) + 1))
    st.dataframe(visible, use_container_width=True, hide_index=True, height=245,
                 column_config={
                     "IMDb Rating": st.column_config.NumberColumn(format="%.1f"),
                     "Votes": st.column_config.NumberColumn(format="%d"),
                     "Worldwide Gross": st.column_config.NumberColumn(format="$%.0f"),
                 })


# Section C Question 6: st.form(), form_submit_button(), session_state.
def movie_search():
    st.markdown('<div class="section-title">🔍 Movie Search (Form + Session State)</div>',
                unsafe_allow_html=True)
    with st.form("movie_search_form"):
        movie_title = st.text_input("Movie Title", placeholder="Enter movie title...")
        preferred_genre = st.selectbox("Preferred Genre", ["Any Genre"] + all_genres)
        minimum_rating = st.slider("Minimum IMDb Rating", 0.0, 10.0, 8.0, 0.1)
        submitted = st.form_submit_button("🔍 Search Movie", use_container_width=True)

    if submitted:
        result = movies.copy()
        if movie_title.strip():
            result = result[result["Title"].str.contains(
                movie_title.strip(), case=False, na=False, regex=False)]
        if preferred_genre != "Any Genre":
            result = result[result["Genre"].apply(
                lambda v: preferred_genre in split_values(v))]
        result = result[result["IMDb Rating"] >= minimum_rating]
        st.session_state.selected_movie = result.iloc[0].to_dict() if not result.empty else None
        if result.empty:
            st.info("No matching movie found. Try different search preferences.")
        else:
            st.success("Movie found successfully!")

    if st.session_state.selected_movie is not None:
        movie = st.session_state.selected_movie
        st.markdown("**🎬 " + str(movie["Title"]).replace("<", "&lt;").replace(">", "&gt;") + "**")
        st.write(f"Genre: {movie['Genre']}")
        st.write(f"IMDb Rating: {movie['IMDb Rating']:.1f}")
        st.write(f"Number of Votes: {movie['Votes']:,}")
        st.dataframe(pd.DataFrame([movie])[["Title", "Genre", "IMDb Rating", "Votes"]],
                     hide_index=True, use_container_width=True)


# Section A Question 1: first 10, shape, columns, dtypes, missing values, success.
def dataset_exploration():
    with st.expander("📋 Section A — Dataset Loading and Initial Exploration", expanded=False):
        st.success(f"Dataset loaded successfully: {csv_files[0].name}")
        st.subheader("First 10 Records")
        st.dataframe(raw_df.head(10), use_container_width=True)
        st.write("Total Rows:", raw_df.shape[0])
        st.write("Total Columns:", raw_df.shape[1])
        st.write("Column Names:", raw_df.columns.tolist())
        st.subheader("Column Data Types")
        st.dataframe(raw_df.dtypes.astype(str).rename("Data Type"), use_container_width=True)
        st.subheader("Missing Values in Each Column")
        st.dataframe(raw_df.isnull().sum().rename("Missing Values"), use_container_width=True)


# ------------------------------------------------------------
# MAIN PAGE
# ------------------------------------------------------------
if page == "🏠 Dashboard":
    banner_path = FOLDER / "banner.png"
    if banner_path.exists():
        st.image(str(banner_path), use_container_width=True)
    else:
        st.title("🎬 IMDb Movie Analytics Dashboard")
        st.subheader("Explore. Analyze. Discover.")

    # Section B Question 2: four KPI metrics in a single row.
    a, b, c, d = st.columns(4)
    with a:
        kpi_card("🎬", "Total Movies", f"{len(movies):,}", "linear-gradient(110deg,#1264b3,#238bd9)")
    with b:
        kpi_card("⭐", "Average IMDb Rating", f"{movies['IMDb Rating'].mean():.1f}",
                 "linear-gradient(110deg,#15935e,#2cb97a)")
    with c:
        kpi_card("🏆", "Highest Rating", f"{movies['IMDb Rating'].max():.1f}",
                 "linear-gradient(110deg,#7832b4,#9850d6)")
    with d:
        kpi_card("👥", "Total Votes", f"{movies['Votes'].sum():,}",
                 "linear-gradient(110deg,#f77a13,#ff951a)")

    st.divider()  # Section B Question 4(c)
    dashboard_charts()
    st.success(f"Dashboard loaded successfully! Explore the top {len(movies)} movies on IMDb.")
    left, right = st.columns([2.1, 1])
    with left:
        movie_explorer()
    with right:
        movie_search()

elif page == "🔎 Movie Explorer":
    st.title("🔎 Interactive Movie Explorer")
    movie_explorer()

else:
    st.title("🔍 Movie Search")
    movie_search()

st.divider()
dataset_exploration()
