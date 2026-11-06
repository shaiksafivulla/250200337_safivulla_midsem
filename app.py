import streamlit as st
import pandas as pd
import plotly.express as px
import re
import ast
from pathlib import Path

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="IMDb Movie Analytics Dashboard",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# SECTION A - DATASET LOADING
# ==========================================

folder = Path(__file__).parent
csv_files = list(folder.glob("*.csv"))

if not csv_files:
    st.error("Please place your IMDb CSV file in the project folder.")
    st.stop()

@st.cache_data
def load_data(path):
    return pd.read_csv(path)

df = load_data(str(csv_files[0]))

# Identify columns
def find_column(*names):
    available = {
        re.sub(r"[^a-z0-9]", "", str(c).lower()): c
        for c in df.columns
    }

    for name in names:
        key = re.sub(r"[^a-z0-9]", "", name.lower())
        if key in available:
            return available[key]

    return None


column_map = {
    "Title": find_column("primaryTitle", "title", "movieTitle"),
    "Genre": find_column("genres", "genre"),
    "Country": find_column(
        "countriesOfOrigin", "countryOfOrigin",
        "countries", "country"
    ),
    "IMDb Rating": find_column(
        "averageRating", "imdbRating", "rating"
    ),
    "Votes": find_column("numVotes", "votes"),
    "Worldwide Gross": find_column(
        "grossWorldwide", "worldwideGross", "gross"
    )
}

missing = [
    name for name, value in column_map.items()
    if value is None
]

if missing:
    st.error("Missing required columns: " + ", ".join(missing))
    st.write("Available columns:", df.columns.tolist())
    st.stop()

movies = df.rename(
    columns={
        original: new
        for new, original in column_map.items()
    }
).copy()


def number(value):
    if pd.isna(value):
        return 0.0

    text = str(value).replace(",", "").replace("$", "").strip()
    match = re.search(r"-?\d+(?:\.\d+)?", text)

    if not match:
        return 0.0

    result = float(match.group())
    suffix = text[match.end():].strip().lower()

    if suffix.startswith("b"):
        result *= 1_000_000_000
    elif suffix.startswith("m"):
        result *= 1_000_000
    elif suffix.startswith("k"):
        result *= 1_000

    return result


def split_items(value):
    if pd.isna(value):
        return []

    text = str(value).strip()

    if text.startswith("[") and text.endswith("]"):
        try:
            items = ast.literal_eval(text)
            if isinstance(items, (list, tuple)):
                return [str(x).strip() for x in items]
        except (ValueError, SyntaxError):
            pass

    return [
        x.strip().strip("'\"[] ")
        for x in re.split(r"[,;|]", text)
        if x.strip().strip("'\"[] ")
    ]


movies["Title"] = movies["Title"].fillna("Unknown").astype(str)
movies["Genre"] = movies["Genre"].fillna("").astype(str)
movies["Country"] = movies["Country"].fillna("").astype(str)

movies["IMDb Rating"] = pd.to_numeric(
    movies["IMDb Rating"], errors="coerce"
)

movies["Votes"] = movies["Votes"].apply(number).astype(int)
movies["Worldwide Gross"] = movies["Worldwide Gross"].apply(number)

genres = sorted({
    g for value in movies["Genre"]
    for g in split_items(value)
})

countries = sorted({
    c for value in movies["Country"]
    for c in split_items(value)
})

# ==========================================
# CUSTOM CSS - DASHBOARD DESIGN
# ==========================================

st.markdown("""
<style>

/* Main background */
.stApp {
    background: linear-gradient(
        120deg, #111827, #1c293d
    );
    color: white;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(
        180deg, #202c40, #151d2b
    );
    border-right: 1px solid #46546a;
}

[data-testid="stSidebar"] * {
    color: white;
}

/* Main page */
.block-container {
    max-width: 1800px;
    padding-top: 1rem;
    padding-bottom: 2rem;
}

/* IMDb logo */
.imdb-logo {
    background: #f5c518;
    color: black !important;
    font-size: 36px;
    font-weight: 900;
    padding: 8px 14px;
    border-radius: 9px;
    display: inline-block;
}

/* Sidebar heading */
.sidebar-title {
    font-size: 23px;
    font-weight: 800;
    margin-top: 15px;
    margin-bottom: 20px;
    line-height: 1.3;
}

/* Sidebar section titles */
.side-heading {
    font-size: 19px;
    font-weight: 750;
    margin-top: 15px;
    margin-bottom: 15px;
}

/* Sidebar details */
.side-detail {
    font-size: 15px;
    line-height: 2;
}

/* Student note */
.student-note {
    background: linear-gradient(
        120deg, #302a4d, #292b49
    );
    border: 1px solid #aa79f2;
    border-left: 5px solid #aa79f2;
    border-radius: 10px;
    padding: 14px;
    margin-top: 65px;
    margin-bottom: 12px;
    font-size: 13px;
    line-height: 1.8;
    color: white;
}

/* Header banner */
.banner {
    background: linear-gradient(
        110deg, #25384e, #111827
    );
    padding: 25px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 15px;
    border: 1px solid #475569;
}

.banner h1 {
    color: white;
    font-size: 35px;
    margin: 0;
}

.banner p {
    font-size: 21px;
    color: white;
    margin: 5px;
}

/* KPI cards */
.kpi {
    padding: 17px;
    border-radius: 12px;
    min-height: 90px;
    display: flex;
    align-items: center;
    gap: 15px;
    margin-bottom: 10px;
    color: white;
}

.kpi-icon {
    font-size: 38px;
}

.kpi-label {
    font-size: 14px;
    font-weight: bold;
}

.kpi-value {
    font-size: 29px;
    font-weight: 850;
}

/* Section heading */
.section-title {
    background: linear-gradient(
        90deg, #30446a, #243247
    );
    padding: 10px;
    border-radius: 8px;
    font-size: 19px;
    font-weight: bold;
    margin-bottom: 12px;
}

/* Chart titles */
.chart-title {
    font-size: 16px;
    font-weight: bold;
    color: white;
    margin-top: 8px;
    margin-bottom: 4px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 12px;
}

.stTabs [data-baseweb="tab"] {
    background: #293750;
    color: white;
    border-radius: 8px 8px 0 0;
}

.stTabs [aria-selected="true"] {
    background: #2389eb !important;
    color: white !important;
}

/* Buttons */
.stButton button {
    border-radius: 8px;
}

[data-testid="stFormSubmitButton"] button {
    background: #875af0;
    color: white;
    border: none;
}

/* Expander */
[data-testid="stExpander"] {
    background: #263349;
    border-radius: 9px;
}

</style>
""", unsafe_allow_html=True)

# ==========================================
# SIDEBAR - UPDATED STUDENT DETAILS
# ==========================================

with st.sidebar:

    st.markdown(
        '<div class="imdb-logo">IMDb</div>',
        unsafe_allow_html=True
    )

    st.markdown(
        '<div class="sidebar-title">'
        'Movie Analytics<br>Dashboard'
        '</div>',
        unsafe_allow_html=True
    )

    st.divider()

    page = st.radio(
        "Navigation",
        [
            "🏠 Dashboard",
            "🔎 Movie Explorer",
            "🔍 Movie Search (Form + Session State)"
        ],
        label_visibility="collapsed"
    )

    st.divider()

    # Dataset metadata
    st.markdown(
        '<div class="side-heading">ℹ️ Dataset Metadata</div>',
        unsafe_allow_html=True
    )

    st.write("📏 **Rows:**", df.shape[0])
    st.write("📐 **Columns:**", df.shape[1])

    with st.expander("🔎 Metadata & Missing Values"):

        st.write("**Column Names:**")
        st.write(df.columns.tolist())

        st.write("**Data Types:**")
        st.write(df.dtypes)

        st.write("**Missing Values:**")
        st.write(df.isnull().sum())

    st.divider()

  # Student details - LEFT SIDEBAR
st.sidebar.markdown(
    '<div class="side-heading">🎓 Student Details</div>',
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    <div class="side-detail">
        👤 <b>Name:</b> Shaik Safivulla<br>
        🏫 <b>Section:</b> Section 1<br>
        📌 <b>Exam:</b> Practical Examination
    </div>
    """,
    unsafe_allow_html=True
)

st.sidebar.markdown(
    """
    <div class="student-note">
        📝 <b>Note: Created by Shaik Safivulla</b><br>
        <b>PRN No:</b> 250200337<br>
        <b>Date:</b> 06/11/2026
    </div>
    """,
    unsafe_allow_html=True
)

# ==========================================
# SESSION STATE
# ==========================================

if "selected_movie" not in st.session_state:
    st.session_state.selected_movie = None

# ==========================================
# KPI CARD FUNCTION
# ==========================================

def kpi_card(icon, title, value, background):

    st.markdown(
        f"""
        <div class="kpi" style="background:{background}">
            <div class="kpi-icon">{icon}</div>
            <div>
                <div class="kpi-label">{title}</div>
                <div class="kpi-value">{value}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# CHART STYLE
# ==========================================

def chart_style(fig, height=280):

    fig.update_layout(
        height=height,
        paper_bgcolor="#f5f8ff",
        plot_bgcolor="#f5f8ff",
        font=dict(color="#17253e", size=12),
        margin=dict(l=15, r=35, t=25, b=30),
        showlegend=False
    )

    fig.update_xaxes(
        tickfont_color="#17253e",
        title_font_color="#17253e",
        gridcolor="#e2e8f0"
    )

    fig.update_yaxes(
        tickfont_color="#17253e",
        title_font_color="#17253e",
        gridcolor="#e2e8f0"
    )

    return fig

# ==========================================
# QUESTION 3A - MOVIES BY GENRE
# ==========================================

def genre_chart(key):

    counts = (
        movies["Genre"]
        .apply(split_items)
        .explode()
        .dropna()
        .value_counts()
        .head(8)
    )

    fig = px.bar(
        x=counts.index,
        y=counts.values,
        text=counts.values,
        labels={"x": "Genre", "y": "Count"}
    )

    fig.update_traces(
        marker_color=[
            "#2186da", "#27b579", "#ffaf28",
            "#9545d6", "#2ba7df", "#e6a01e",
            "#4879e9", "#17a592"
        ][:len(counts)],
        textposition="outside"
    )

    st.plotly_chart(
        chart_style(fig),
        use_container_width=True,
        key=key,
        config={"displayModeBar": False}
    )

# ==========================================
# QUESTION 3B - RATING HISTOGRAM
# ==========================================

def rating_chart(key):

    fig = px.histogram(
        movies.dropna(subset=["IMDb Rating"]),
        x="IMDb Rating",
        nbins=15
    )

    fig.update_traces(
        marker_color="#2c85f6",
        marker_line_color="white",
        marker_line_width=1
    )

    fig.update_layout(
        xaxis_title="IMDb Rating",
        yaxis_title="Count"
    )

    st.plotly_chart(
        chart_style(fig),
        use_container_width=True,
        key=key,
        config={"displayModeBar": False}
    )

# ==========================================
# QUESTION 3C - RATING VS VOTES
# ==========================================

def votes_chart(key):

    fig = px.scatter(
        movies.dropna(subset=["IMDb Rating"]),
        x="IMDb Rating",
        y="Votes",
        hover_name="Title"
    )

    fig.update_traces(
        marker=dict(
            size=7,
            color="#248cf0",
            opacity=0.85
        )
    )

    fig.update_layout(
        xaxis_title="IMDb Rating",
        yaxis_title="Number of Votes"
    )

    st.plotly_chart(
        chart_style(fig),
        use_container_width=True,
        key=key,
        config={"displayModeBar": False}
    )

# ==========================================
# QUESTION 3D - WORLDWIDE GROSS
# ==========================================

def gross_chart(key):

    top10 = (
        movies.sort_values(
            "Worldwide Gross",
            ascending=False
        )
        .head(10)
        .sort_values("Worldwide Gross")
        .copy()
    )

    top10["Gross Label"] = top10["Worldwide Gross"].apply(
        lambda x: f"${x / 1e9:.2f}B"
        if x >= 1e9
        else f"${x / 1e6:.0f}M"
    )

    fig = px.bar(
        top10,
        x="Worldwide Gross",
        y="Title",
        orientation="h",
        text="Gross Label"
    )

    fig.update_traces(
        marker_color="#ff921b",
        textposition="outside",
        cliponaxis=False
    )

    fig.update_layout(
        xaxis_title="Worldwide Gross (USD)",
        yaxis_title=None,
        margin=dict(l=15, r=85, t=20, b=30)
    )

    st.plotly_chart(
        chart_style(fig, height=310),
        use_container_width=True,
        key=key,
        config={"displayModeBar": False}
    )

# ==========================================
# QUESTION 4 - DASHBOARD TABS
# ==========================================

def dashboard_charts():

    tab1, tab2, tab3 = st.tabs([
        "📊 Genre Analysis",
        "📈 Rating Analysis",
        "🪙 Gross Collection"
    ])

    with tab1:

        c1, c2 = st.columns(2)

        with c1:
            st.markdown(
                '<div class="chart-title">📊 Movies by Genre</div>',
                unsafe_allow_html=True
            )
            genre_chart("genre_main")

        with c2:
            st.markdown(
                '<div class="chart-title">📊 IMDb Rating Distribution</div>',
                unsafe_allow_html=True
            )
            rating_chart("rating_main")

        c3, c4 = st.columns(2)

        with c3:
            st.markdown(
                '<div class="chart-title">💠 Rating vs Number of Votes</div>',
                unsafe_allow_html=True
            )
            votes_chart("votes_main")

        with c4:
            st.markdown(
                '<div class="chart-title">🏆 Top 10 Movies by Worldwide Gross</div>',
                unsafe_allow_html=True
            )
            gross_chart("gross_main")

    with tab2:

        c1, c2 = st.columns(2)

        with c1:
            st.subheader("IMDb Rating Distribution")
            rating_chart("rating_tab")

        with c2:
            st.subheader("Rating vs Number of Votes")
            votes_chart("votes_tab")

    with tab3:

        st.subheader("Top 10 Movies by Worldwide Gross")
        gross_chart("gross_tab")

# ==========================================
# QUESTION 5 - RESET FILTERS
# ==========================================

def reset_filters():

    st.session_state["genre_filter"] = "All Genres"
    st.session_state["country_filter"] = []
    st.session_state["rating_filter"] = (0.0, 10.0)
    st.session_state["votes_filter"] = 0
    st.session_state["title_filter"] = ""
    st.session_state["sort_filter"] = "Descending"

# ==========================================
# QUESTION 5 - INTERACTIVE EXPLORER
# ==========================================

def movie_explorer():

    st.markdown(
        '<div class="section-title">'
        '🔎 Interactive Movie Explorer'
        '</div>',
        unsafe_allow_html=True
    )

    c1, c2, c3, c4, c5, c6 = st.columns(
        [1.2, 1.3, 1.6, 1.1, 1.6, 1.2]
    )

    with c1:
        genre = st.selectbox(
            "Genre",
            ["All Genres"] + genres,
            key="genre_filter"
        )

    with c2:
        selected_countries = st.multiselect(
            "Countries",
            countries,
            key="country_filter"
        )

    with c3:
        min_rating, max_rating = st.slider(
            "IMDb Rating",
            0.0,
            10.0,
            (0.0, 10.0),
            0.1,
            key="rating_filter"
        )

    with c4:
        min_votes = st.number_input(
            "Min Votes",
            min_value=0,
            step=10000,
            key="votes_filter"
        )

    with c5:
        title = st.text_input(
            "Search Title",
            placeholder="Enter movie title...",
            key="title_filter"
        )

    with c6:
        order = st.radio(
            "Sort Order",
            ["Ascending", "Descending"],
            index=1,
            key="sort_filter"
        )

    # Filter same DataFrame
    filtered_df = movies.copy()

    if genre != "All Genres":
        filtered_df = filtered_df[
            filtered_df["Genre"].apply(
                lambda x: genre in split_items(x)
            )
        ]

    if selected_countries:
        filtered_df = filtered_df[
            filtered_df["Country"].apply(
                lambda x: bool(
                    set(selected_countries).intersection(
                        split_items(x)
                    )
                )
            )
        ]

    filtered_df = filtered_df[
        filtered_df["IMDb Rating"].between(
            min_rating, max_rating
        )
    ]

    filtered_df = filtered_df[
        filtered_df["Votes"] >= min_votes
    ]

    if title.strip():
        filtered_df = filtered_df[
            filtered_df["Title"].str.contains(
                title.strip(),
                case=False,
                na=False,
                regex=False
            )
        ]

    filtered_df = filtered_df.sort_values(
        "IMDb Rating",
        ascending=(order == "Ascending")
    )

    c1, c2 = st.columns([1.3, 5])

    with c1:
        st.info(f"Filtered Movies: {len(filtered_df)}")

    with c2:
        st.button(
            "🔄 Reset Filters",
            on_click=reset_filters,
            key="reset_button"
        )

    result = filtered_df[
        [
            "Title",
            "Genre",
            "Country",
            "IMDb Rating",
            "Votes",
            "Worldwide Gross"
        ]
    ].copy()

    result.insert(0, "#", range(1, len(result) + 1))

    st.dataframe(
        result,
        use_container_width=True,
        hide_index=True,
        height=250
    )

# ==========================================
# QUESTION 6 - MOVIE SEARCH FORM
# ==========================================

def movie_search():

    st.markdown(
        '<div class="section-title">'
        '🔍 Movie Search (Form + Session State)'
        '</div>',
        unsafe_allow_html=True
    )

    with st.form("movie_search_form"):

        movie_title = st.text_input(
            "Movie Title",
            placeholder="Enter movie title..."
        )

        preferred_genre = st.selectbox(
            "Preferred Genre",
            ["Any Genre"] + genres
        )

        minimum_rating = st.slider(
            "Minimum IMDb Rating",
            0.0,
            10.0,
            8.0,
            0.1
        )

        submitted = st.form_submit_button(
            "🔍 Search Movie",
            use_container_width=True
        )

    if submitted:

        result = movies.copy()

        if movie_title.strip():
            result = result[
                result["Title"].str.contains(
                    movie_title.strip(),
                    case=False,
                    na=False,
                    regex=False
                )
            ]

        if preferred_genre != "Any Genre":
            result = result[
                result["Genre"].apply(
                    lambda x: preferred_genre in split_items(x)
                )
            ]

        result = result[
            result["IMDb Rating"] >= minimum_rating
        ]

        if result.empty:

            st.session_state.selected_movie = None

            st.info(
                "No matching movie found. Try different preferences."
            )

        else:

            st.session_state.selected_movie = (
                result.iloc[0].to_dict()
            )

            st.success("Movie found successfully!")

    if st.session_state.selected_movie is not None:

        movie = st.session_state.selected_movie

        st.markdown(f"### 🎬 {movie['Title']}")

        st.write("Genre:", movie["Genre"])

        st.write(
            "IMDb Rating:",
            f"{movie['IMDb Rating']:.1f}"
        )

        st.write(
            "Number of Votes:",
            f"{movie['Votes']:,}"
        )

        st.dataframe(
            pd.DataFrame([movie])[
                ["Title", "Genre", "IMDb Rating", "Votes"]
            ],
            hide_index=True,
            use_container_width=True
        )

# ==========================================
# SECTION A - DATASET EXPLORATION
# ==========================================

def dataset_information():

    with st.expander(
        "📋 Dataset Loading and Initial Exploration"
    ):

        st.success("Dataset loaded successfully!")

        st.subheader("First 10 Records")
        st.dataframe(
            df.head(10),
            use_container_width=True
        )

        st.subheader("Dataset Shape")
        st.write("Total Rows:", df.shape[0])
        st.write("Total Columns:", df.shape[1])

        st.subheader("Column Names")
        st.write(df.columns.tolist())

        st.subheader("Column Data Types")
        st.write(df.dtypes)

        st.subheader("Missing Values")
        st.write(df.isnull().sum())

# ==========================================
# MAIN APPLICATION
# ==========================================

if page == "🏠 Dashboard":

    banner_file = folder / "banner.png"

    if banner_file.exists():
        st.image(
            str(banner_file),
            use_container_width=True
        )
    else:
        st.markdown("""
        <div class="banner">
            <h1>🎬 IMDb Movie Analytics Dashboard</h1>
            <p>Explore. Analyze. Discover.</p>
        </div>
        """, unsafe_allow_html=True)

    # Four KPI metrics
    k1, k2, k3, k4 = st.columns(4)

    with k1:
        kpi_card(
            "🎬",
            "Total Movies",
            f"{len(movies):,}",
            "linear-gradient(110deg,#1264b3,#238bd9)"
        )

    with k2:
        kpi_card(
            "⭐",
            "Average IMDb Rating",
            f"{movies['IMDb Rating'].mean():.1f}",
            "linear-gradient(110deg,#15935e,#2cb97a)"
        )

    with k3:
        kpi_card(
            "🏆",
            "Highest Rating",
            f"{movies['IMDb Rating'].max():.1f}",
            "linear-gradient(110deg,#7832b4,#9850d6)"
        )

    with k4:
        kpi_card(
            "👥",
            "Total Votes",
            f"{movies['Votes'].sum():,}",
            "linear-gradient(110deg,#f77a13,#ff951a)"
        )

    st.divider()

    dashboard_charts()

    st.success(
        f"Dashboard loaded successfully! "
        f"Enjoy exploring the top {len(movies)} movies on IMDb."
    )

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
dataset_information()