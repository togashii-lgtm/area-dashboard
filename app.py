"""
商圏エリアデータダッシュボード
愛知県11市の人口・住宅着工統計を可視化する社内マーケティングツール
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

# ============================================================
# ページ設定＆モバイル最適化CSS
# ============================================================

st.set_page_config(
    page_title="商圏エリアデータダッシュボード",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.25rem !important; }
        h3 { font-size: 1.1rem !important; }
        .stMetric { padding: 8px !important; }
    }
    .guide-box {
        background-color: #f0f7ff;
        border-left: 4px solid #1f77b4;
        padding: 12px 16px;
        border-radius: 4px;
        margin-bottom: 14px;
        font-size: 0.9rem;
        line-height: 1.5;
    }
    .guide-box-title {
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 6px;
    }
    .guide-item {
        margin-bottom: 4px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# パスワード認証
# ============================================================

def check_password():
    try:
        correct_password = st.secrets["password"]
    except (FileNotFoundError, KeyError):
        return True

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.markdown("## 🔐 ログイン")
    st.markdown("このダッシュボードは社内限定です。パスワードを入力してください。")

    password = st.text_input("パスワード", type="password", key="password_input")
    if st.button("ログイン", type="primary"):
        if password == correct_password:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません。")

    return False


if not check_password():
    st.stop()

# ============================================================
# データ読み込み
# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


@st.cache_data(ttl=3600)
def load_data():
    pop_path = os.path.join(DATA_DIR, "population.csv")
    housing_path = os.path.join(DATA_DIR, "housing.csv")
    od_path = os.path.join(DATA_DIR, "migration_od.csv")

    dfs = {}
    if os.path.exists(pop_path):
        df_p = pd.read_csv(pop_path, dtype={"city_code": str, "year": str})
        df_p["value"] = pd.to_numeric(df_p["value"], errors="coerce")
        df_p["year"] = df_p["year"].astype(str)
        dfs["population"] = df_p
    else:
        dfs["population"] = pd.DataFrame()

    if os.path.exists(housing_path):
        df_h = pd.read_csv(housing_path, dtype={"city_code": str, "year": str})
        df_h["value"] = pd.to_numeric(df_h["value"], errors="coerce")
        df_h["year"] = df_h["year"].astype(str)
        dfs["housing"] = df_h
    else:
        dfs["housing"] = pd.DataFrame()

    if os.path.exists(od_path):
        df_od = pd.read_csv(od_path, dtype={"city_code": str, "partner_code": str, "year": str})
        df_od["persons"] = pd.to_numeric(df_od["persons"], errors="coerce")
        dfs["migration_od"] = df_od
    else:
        dfs["migration_od"] = pd.DataFrame()

    return dfs


data = load_data()
df_pop = data["population"]
df_housing = data["housing"]
df_od = data["migration_od"]

# ============================================================
# 市の定義＆地理座標（緯度・経度）
# ============================================================

CITIES = {
    "23202": {"name": "岡崎市", "area": "西三河", "lat": 34.9554, "lon": 137.1729},
    "23209": {"name": "碧南市", "area": "西三河", "lat": 34.8845, "lon": 136.9953},
    "23210": {"name": "刈谷市", "area": "西三河", "lat": 34.9892, "lon": 136.9984},
    "23211": {"name": "豊田市", "area": "西三河", "lat": 35.0831, "lon": 137.1558},
    "23212": {"name": "安城市", "area": "西三河", "lat": 34.9599, "lon": 137.0805},
    "23213": {"name": "西尾市", "area": "西三河", "lat": 34.8637, "lon": 137.0583},
    "23222": {"name": "東海市", "area": "知多",   "lat": 35.0253, "lon": 136.9066},
    "23223": {"name": "大府市", "area": "知多",   "lat": 35.0084, "lon": 136.9609},
    "23224": {"name": "知多市", "area": "知多",   "lat": 34.9951, "lon": 136.8653},
    "23225": {"name": "知立市", "area": "西三河", "lat": 35.0069, "lon": 137.0401},
    "23227": {"name": "高浜市", "area": "西三河", "lat": 34.9272, "lon": 136.9896},
}

# 主な周辺自治体・移動元の緯度経度
MIGRATION_GEO_COORDS = {
    # 11市
    "岡崎市": (34.9554, 137.1729),
    "碧南市": (34.8845, 136.9953),
    "刈谷市": (34.9892, 136.9984),
    "豊田市": (35.0831, 137.1558),
    "安城市": (34.9599, 137.0805),
    "西尾市": (34.8637, 137.0583),
    "東海市": (35.0253, 136.9066),
    "大府市": (35.0084, 136.9609),
    "知多市": (34.9951, 136.8653),
    "知立市": (35.0069, 137.0401),
    "高浜市": (34.9272, 136.9896),
    # 名古屋市および各区
    "名古屋市": (35.1815, 136.9064),
    "緑区": (35.0862, 136.9658),
    "南区": (35.0975, 136.9328),
    "中区": (35.1709, 136.9077),
    "天白区": (35.1294, 136.9856),
    "名東区": (35.1742, 137.0089),
    "熱田区": (35.1272, 136.9084),
    "港区": (35.1086, 136.8833),
    "瑞穂区": (35.1325, 136.9347),
    "昭和区": (35.1481, 136.9367),
    "千種区": (35.1664, 136.9500),
    "東区": (35.1800, 136.9333),
    "中村区": (35.1706, 136.8647),
    "西区": (35.1950, 136.8850),
    "北区": (35.2150, 136.9150),
    "守山区": (35.2000, 136.9833),
    "中川区": (35.1389, 136.8600),
    # 近隣市町村
    "みよし市": (35.0772, 137.0789),
    "半田市": (34.8919, 136.9328),
    "豊明市": (35.0531, 137.0142),
    "日進市": (35.1311, 137.0433),
    "東郷町": (35.0878, 137.0431),
    "東浦町": (34.9753, 136.9697),
    "阿久比町": (34.9317, 136.9189),
    "武豊町": (34.8519, 136.9197),
    "常滑市": (34.8872, 136.8378),
    "幸田町": (34.8631, 137.1644),
    "蒲郡市": (34.8275, 137.2217),
    "豊川市": (34.8256, 137.3934),
    "豊橋市": (34.7692, 137.3914),
    "新城市": (34.9031, 137.4961),
    "田原市": (34.6681, 137.2661),
    "長久手市": (35.1833, 137.0500),
    "瀬戸市": (35.2231, 137.0847),
    "春日井市": (35.2472, 136.9728),
    "小牧市": (35.2900, 136.9100),
    "一宮市": (35.3083, 136.8000),
    "津島市": (35.1767, 136.7267),
    "愛西市": (35.1500, 136.7333),
    "弥富市": (35.1139, 136.7236),
    "あま市": (35.1917, 136.7972),
    "清須市": (35.2000, 136.8500),
    "北名古屋市": (35.2417, 136.8722),
    # 広域主要地域
    "東京都特別区部": (35.6895, 139.6917),
    "浜松市": (34.7108, 137.7261),
    "四日市市": (34.9653, 136.6247),
    "桑名市": (35.0644, 136.6833),
    "鈴鹿市": (34.8822, 136.5839),
    "岐阜市": (35.4233, 136.7606),
}

CITY_NAMES = {v["name"]: k for k, v in CITIES.items()}
ALL_CITY_NAMES = [CITIES[k]["name"] for k in sorted(CITIES.keys())]

CITY_COLORS = {
    "岡崎市": "#1f77b4", "碧南市": "#aec7e8", "刈谷市": "#ff7f0e",
    "豊田市": "#ffbb78", "安城市": "#2ca02c", "西尾市": "#98df8a",
    "東海市": "#d62728", "大府市": "#ff9896", "知多市": "#9467bd",
    "知立市": "#c5b0d5", "高浜市": "#8c564b",
}

# ============================================================
# サイドバー
# ============================================================

with st.sidebar:
    st.markdown("## 🏠 商圏エリアダッシュボード")
    st.markdown("**愛知県11市** の市場データ分析ツール")
    st.markdown("---")

    area_filter = st.multiselect(
        "エリアで絞り込み",
        ["西三河", "知多"],
        default=["西三河", "知多"],
    )

    available_cities = [
        CITIES[k]["name"]
        for k in sorted(CITIES.keys())
        if CITIES[k]["area"] in area_filter
    ]

    if "selected_cities" not in st.session_state:
        st.session_state["selected_cities"] = available_cities
    else:
        st.session_state["selected_cities"] = [
            c for c in st.session_state["selected_cities"] if c in available_cities
        ]

    st.markdown("#### 対象市の選択")
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("✅ 全選択", use_container_width=True):
        st.session_state["selected_cities"] = available_cities
        st.rerun()
    if btn_col2.button("🧹 全解除", use_container_width=True):
        st.session_state["selected_cities"] = []
        st.rerun()

    selected_cities = st.multiselect(
        "対象市を選択（複数可）",
        available_cities,
        default=st.session_state["selected_cities"],
        key="city_selector"
    )
    st.session_state["selected_cities"] = selected_cities

    st.markdown("---")
    st.markdown("### 📊 時系列グラフの表示期間")

    year_range_pop = st.slider(
        "人口・世帯データの年範囲",
        min_value=1980, max_value=2025,
        value=(2000, 2024),
        key="year_pop"
    )

    year_range_housing = st.slider(
        "住宅着工データの年範囲",
        min_value=2000, max_value=2025,
        value=(2005, 2024),
        key="year_housing"
    )

    st.markdown("---")
    st.caption("データ出典: e-Stat（政府統計の総合窓口）")
    st.caption("・社会・人口統計体系（総務省統計局）")
    st.caption("・建築着工統計調査（国土交通省）")
    st.caption("・住民基本台帳人口移動報告（2022年）")


selected_codes = [CITY_NAMES[name] for name in selected_cities if name in CITY_NAMES]

if not selected_codes:
    st.warning("⚠️ サイドバーから対象市を1つ以上選択してください。（「全選択」ボタンで一括選択できます）")
    st.stop()


# ============================================================
# 解説コンポーネント
# ============================================================

def show_guide(title, rule, meaning, business_point):
    with st.expander(f"💡 【解説】{title} の集計ルールと見方（クリックで開閉）"):
        st.markdown(
            f"""
            <div class="guide-box">
                <div class="guide-box-title">📌 {title} とは？</div>
                <div class="guide-item"><b>【集計ルール】</b> {rule}</div>
                <div class="guide-item"><b>【数字から何が分かるか】</b> {meaning}</div>
                <div class="guide-item"><b>【事業への活かし方（狙い目）】</b> {business_point}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# ============================================================
# グラフ描画ヘルパー関数
# ============================================================

def filter_df(df, codes, indicator_code, year_min, year_max):
    mask = (
        df["city_code"].isin(codes)
        & (df["indicator_code"] == indicator_code)
        & (df["year"].astype(int) >= year_min)
        & (df["year"].astype(int) <= year_max)
    )
    return df[mask].copy()


def filter_df_multi(df, codes, indicator_codes, year_min, year_max):
    mask = (
        df["city_code"].isin(codes)
        & (df["indicator_code"].isin(indicator_codes))
        & (df["year"].astype(int) >= year_min)
        & (df["year"].astype(int) <= year_max)
    )
    return df[mask].copy()


def make_line_chart(df, title, y_label="値", color_col="city_name"):
    fig = px.line(
        df.sort_values(["city_name", "year"]),
        x="year", y="value",
        color=color_col,
        markers=True,
        title=title,
        labels={"year": "年", "value": y_label, "city_name": "市"},
        color_discrete_map=CITY_COLORS,
    )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
        margin=dict(l=15, r=15, t=40, b=40),
        height=380,
    )
    return fig


def make_bar_chart(df, title, y_label="値", color_col="city_name", barmode="group"):
    fig = px.bar(
        df.sort_values(["year", "city_name"]),
        x="year", y="value",
        color=color_col,
        barmode=barmode,
        title=title,
        labels={"year": "年", "value": y_label, "city_name": "市"},
        color_discrete_map=CITY_COLORS,
    )
    fig.update_layout(
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
        margin=dict(l=15, r=15, t=40, b=40),
        height=380,
    )
    return fig


def make_pivot_table(df, value_col="value", index_col="year", columns_col="city_name"):
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(
        values=value_col, index=index_col, columns=columns_col, aggfunc="first"
    )
    pivot = pivot.sort_index(ascending=False)
    return pivot


def download_button(df, filename, label="📥 表データをCSVダウンロード"):
    csv_data = df.to_csv(index=True, encoding="utf-8-sig")
    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )


# ============================================================
# メインコンテンツ
# ============================================================

st.title("🏠 商圏エリアデータダッシュボード")
st.caption(f"選択中: {', '.join(selected_cities)}（計 {len(selected_cities)} 市）")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📋 概要・KPI",
    "👥 人口・世帯構造",
    "🚚 人の移動（地図フローマップ）",
    "🏗️ 住宅着工統計",
    "🏘️ 住宅ストック・空き家",
    "📖 指標解説ガイド",
])

# ============================================================
# タブ1: 概要・KPI（期間選択：今年・前年・任意対応）
# ============================================================
with tab1:
    st.header("📋 商圏サマリー・ランキング")
    
    show_guide(
        "商圏サマリーとKPIの見方",
        "選択した年次（今年・前年・任意の年）の各市数値を合算・ランキング化したものです。",
        "選択した商圏全体の市場規模感（総人口・年間着工総数）と、どの自治体が最大のマーケットボリュームを持っているかが一目で分かります。",
        "着工戸数上位の市は『シェア拡大・主力営業エリア』、人口・世帯が増加している市は『木造賃貸アパートや分譲の新規開拓エリア』としてリソース配分を検討できます。"
    )

    if not df_housing.empty:
        starts_years = sorted(df_housing["year"].dropna().astype(int).unique(), reverse=True)
        max_year = starts_years[0] if starts_years else 2024
        prev_year = starts_years[1] if len(starts_years) > 1 else max_year - 1

        st.markdown("#### 📅 集計対象の年を選択")
        period_col1, period_col2 = st.columns([2, 3])
        with period_col1:
            period_mode = st.radio(
                "表示基準年",
                [f"最新年（{max_year}年）", f"前年（{prev_year}年）", "任意の年を指定"],
                horizontal=True,
                key="summary_period_mode"
            )

        with period_col2:
            if period_mode == f"最新年（{max_year}年）":
                target_year = max_year
            elif period_mode == f"前年（{prev_year}年）":
                target_year = prev_year
            else:
                target_year = st.selectbox(
                    "年を選択してください",
                    starts_years,
                    index=0,
                    key="custom_target_year"
                )

        st.info(f"📌 現在 **【{target_year}年】** のデータを表示中")

        pop_years = sorted(df_pop["year"].dropna().astype(int).unique(), reverse=True)
        matched_pop_years = [y for y in pop_years if y <= target_year]
        target_pop_year = matched_pop_years[0] if matched_pop_years else (pop_years[0] if pop_years else 2020)

        target_starts = df_housing[
            (df_housing["city_code"].isin(selected_codes))
            & (df_housing["year"].astype(int) == target_year)
        ].copy()

        prior_year = target_year - 1
        prior_starts = df_housing[
            (df_housing["city_code"].isin(selected_codes))
            & (df_housing["year"].astype(int) == prior_year)
        ].copy()

        target_pop = df_pop[
            (df_pop["city_code"].isin(selected_codes))
            & (df_pop["indicator_code"] == "A1101")
            & (df_pop["year"].astype(int) == target_pop_year)
        ].copy()

        def get_sum(df, ind_code):
            sub = df[df["indicator_code"] == ind_code]
            return sub["value"].sum() if not sub.empty else 0

        tot_starts = get_sum(target_starts, "H1800")
        prior_tot_starts = get_sum(prior_starts, "H1800")
        diff_tot = tot_starts - prior_tot_starts if prior_tot_starts > 0 else None
        pct_tot = (diff_tot / prior_tot_starts * 100) if (diff_tot is not None and prior_tot_starts > 0) else None

        tot_kashiya = get_sum(target_starts, "H1802")
        prior_kashiya = get_sum(prior_starts, "H1802")
        diff_kashiya = tot_kashiya - prior_kashiya if prior_kashiya > 0 else None
        pct_kashiya = (diff_kashiya / prior_kashiya * 100) if (diff_kashiya is not None and prior_kashiya > 0) else None

        tot_bunjou = get_sum(target_starts, "H1803")
        prior_bunjou = get_sum(prior_starts, "H1803")
        diff_bunjou = tot_bunjou - prior_bunjou if prior_bunjou > 0 else None
        pct_bunjou = (diff_bunjou / prior_bunjou * 100) if (diff_bunjou is not None and prior_bunjou > 0) else None

        tot_pop = target_pop["value"].sum() if not target_pop.empty else 0

        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            st.metric(
                "総人口（選択市合計）",
                f"{tot_pop:,.0f} 人",
                help=f"{target_pop_year}年時点の国勢調査人口（※人口統計は5年周期調査のため、{target_year}年時点に最も近い年を表示）"
            )
        with kpi_col2:
            delta_str = f"{diff_tot:+,.0f} 戸 ({pct_tot:+.1f}%)" if diff_tot is not None else None
            st.metric(
                f"年間着工戸数（{target_year}年 合計）",
                f"{tot_starts:,.0f} 戸",
                delta=delta_str,
                help=f"{target_year}年 新設住宅着工総数（前年{prior_year}年比）"
            )

        kpi_col3, kpi_col4 = st.columns(2)
        with kpi_col3:
            delta_kashiya = f"{diff_kashiya:+,.0f} 戸 ({pct_kashiya:+.1f}%)" if diff_kashiya is not None else None
            st.metric(
                f"貸家着工（{target_year}年 賃貸アパート等）",
                f"{tot_kashiya:,.0f} 戸",
                delta=delta_kashiya,
                help=f"{target_year}年 アパート・賃貸住宅着工数（前年比）"
            )
        with kpi_col4:
            delta_bunjou = f"{diff_bunjou:+,.0f} 戸 ({pct_bunjou:+.1f}%)" if diff_bunjou is not None else None
            st.metric(
                f"分譲住宅（{target_year}年 建売＋マンション合算）",
                f"{tot_bunjou:,.0f} 戸",
                delta=delta_bunjou,
                help=f"【国土交通省定義】分譲住宅着工数 ＝『建売一戸建て住宅』＋『分譲マンション（共同住宅）』の合算値です（前年比）。"
            )

        st.markdown("---")

        st.subheader(f"🏆 商圏内ランキング比較（{target_year}年基準）")
        rank_col1, rank_col2 = st.columns(2)

        with rank_col1:
            st.markdown(f"**人口規模ランキング（{target_pop_year}年）**")
            if not target_pop.empty:
                rank_pop = target_pop[["city_name", "value"]].sort_values("value", ascending=False).reset_index(drop=True)
                rank_pop.index = rank_pop.index + 1
                rank_pop.columns = ["市名", "人口（人）"]
                rank_pop["人口（人）"] = rank_pop["人口（人）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(rank_pop, use_container_width=True)

        with rank_col2:
            st.markdown(f"**新設住宅着工戸数ランキング（{target_year}年）**")
            starts_sub = target_starts[target_starts["indicator_code"] == "H1800"]
            if not starts_sub.empty:
                rank_starts = starts_sub[["city_name", "value"]].sort_values("value", ascending=False).reset_index(drop=True)
                rank_starts.index = rank_starts.index + 1
                rank_starts.columns = ["市名", "着工数（戸）"]
                rank_starts["着工数（戸）"] = rank_starts["着工数（戸）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(rank_starts, use_container_width=True)

        st.subheader(f"📊 着工新設住宅の商圏シェア（{target_year}年）")
        if not starts_sub.empty:
            fig_share = px.pie(
                starts_sub, values="value", names="city_name",
                color="city_name", color_discrete_map=CITY_COLORS,
            )
            fig_share.update_traces(textinfo="label+percent")
            fig_share.update_layout(
                height=350,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="top", y=-0.1, xanchor="center", x=0.5)
            )
            st.plotly_chart(fig_share, use_container_width=True)


# ============================================================
# タブ2: 人口・世帯構造（単身・家族・現住居持ち家/借家）
# ============================================================
with tab2:
    st.header("👥 人口・世帯構造（一人暮らし・家族・持ち家比率）")

    if not df_pop.empty:
        y_min, y_max = year_range_pop

        st.subheader("1. 世帯数推移と世帯構成（一人暮らし vs 家族）")
        show_guide(
            "単独世帯（一人暮らし）と核家族世帯（家族）",
            "国勢調査による世帯構造の内訳。①単独世帯＝1人暮らし、②核家族世帯＝夫婦のみ・夫婦と子・ひとり親と子、③その他親族世帯＝二世代・三世代同居など。",
            "『住宅を借りる・建てる単位は人頭ではなく世帯』です。単身世帯の増加はアパート需要に直結し、核家族世帯は注文・分譲住宅のメインターゲットになります。",
            "単身世帯急増エリアは『木造単身向け賃貸アパート』の最適地。核家族世帯が多いエリアは『ファミリー向け分譲・注文住宅』に注力すべきです。"
        )

        detail_city_hh = st.selectbox(
            "世帯構成の内訳を見る市を選択してください",
            selected_cities,
            key="detail_city_hh"
        )
        detail_code_hh = CITY_NAMES.get(detail_city_hh, "")

        if detail_code_hh:
            hh_codes = {
                "A810105": "単独世帯(一人暮らし)",
                "A810102": "核家族世帯(ファミリー)",
                "A810103": "その他親族世帯(二・三世代)"
            }
            df_hh = filter_df_multi(df_pop, [detail_code_hh], list(hh_codes.keys()), 1980, 2025)
            if not df_hh.empty:
                df_hh["hh_type"] = df_hh["indicator_code"].map(hh_codes)
                fig_hh = px.bar(
                    df_hh.sort_values("year"),
                    x="year", y="value", color="hh_type",
                    barmode="stack",
                    title=f"{detail_city_hh}：世帯構成の推移（一人暮らし vs ファミリー）",
                    labels={"year": "年", "value": "世帯数", "hh_type": "世帯タイプ"},
                    color_discrete_map={
                        "単独世帯(一人暮らし)": "#ff7f0e",
                        "核家族世帯(ファミリー)": "#1f77b4",
                        "その他親族世帯(二・三世代)": "#2ca02c"
                    },
                )
                fig_hh.update_layout(
                    height=380,
                    legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
                    margin=dict(l=15, r=15, t=40, b=40),
                )
                st.plotly_chart(fig_hh, use_container_width=True)

                pivot_hh = df_hh.pivot_table(
                    values="value", index="year", columns="hh_type", aggfunc="first"
                ).sort_index(ascending=False)
                st.dataframe(pivot_hh.style.format("{:,.0f}"), use_container_width=True)

        st.markdown("---")

        st.subheader("2. 現住居の所有形態（持ち家世帯 vs 持ち家以外/賃貸世帯）")
        show_guide(
            "現住居の持ち家世帯数 vs 借家（持ち家以外）世帯数",
            "住宅・土地統計調査に基づく、今住んでいる住居が『自己所有（持ち家）』か『賃貸（借家＝民間アパート・公営等）』かの世帯数。",
            "【持ち家世帯＝リフォーム・建替え・アパート土地活用のターゲット】\n【借家世帯＝これから持ち家を建てる/買う一次取得の最大の見込み客プール、または優良賃貸への住み替え層】。",
            "借家世帯数が多く比率が高い市は、注文住宅の一次取得営業や分譲建売の反響が非常に獲りやすいエリアです。"
        )

        detail_city_tenure = st.selectbox(
            "住宅所有関係を見る市を選択してください",
            selected_cities,
            key="detail_city_tenure"
        )
        detail_code_tenure = CITY_NAMES.get(detail_city_tenure, "")

        if detail_code_tenure and not df_housing.empty:
            tenure_codes = {
                "H1310": "持ち家世帯",
                "H1322": "民営借家(アパート・マンション等)",
                "H1321": "公営・UR借家"
            }
            df_tenure = filter_df_multi(df_housing, [detail_code_tenure], list(tenure_codes.keys()), 1980, 2025)
            if not df_tenure.empty:
                df_tenure["tenure_type"] = df_tenure["indicator_code"].map(tenure_codes)
                fig_tenure = px.bar(
                    df_tenure.sort_values("year"),
                    x="year", y="value", color="tenure_type",
                    barmode="stack",
                    title=f"{detail_city_tenure}：現住居の所有形態（持ち家 vs 賃貸世帯数）",
                    labels={"year": "年", "value": "世帯数", "tenure_type": "所有関係"},
                    color_discrete_map={
                        "持ち家世帯": "#1f77b4",
                        "民営借家(アパート・マンション等)": "#ff7f0e",
                        "公営・UR借家": "#aec7e8"
                    },
                )
                fig_tenure.update_layout(
                    height=380,
                    legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
                    margin=dict(l=15, r=15, t=40, b=40),
                )
                st.plotly_chart(fig_tenure, use_container_width=True)

                pivot_tenure = df_tenure.pivot_table(
                    values="value", index="year", columns="tenure_type", aggfunc="first"
                ).sort_index(ascending=False)
                st.dataframe(pivot_tenure.style.format("{:,.0f}"), use_container_width=True)

        st.markdown("---")

        st.subheader("3. 総人口の推移")
        df_total_pop = filter_df(df_pop, selected_codes, "A1101", y_min, y_max)
        if not df_total_pop.empty:
            fig = make_line_chart(df_total_pop, "総人口の推移（人）", "人口（人）")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("4. 年齢3区分（子育て世代・現役・シニア）")
        age_codes = {"A1301": "15歳未満(子育て層)", "A1302": "15-64歳(生産年齢)", "A1303": "65歳以上(シニア層)"}
        df_age = filter_df_multi(df_pop, selected_codes, list(age_codes.keys()), y_min, y_max)
        if not df_age.empty:
            df_age["year_int"] = df_age["year"].astype(int)
            latest_age_year = df_age["year_int"].max()
            df_age_latest = df_age[df_age["year_int"] == latest_age_year].copy()
            df_age_latest["age_group"] = df_age_latest["indicator_code"].map(age_codes)

            fig_age = px.bar(
                df_age_latest.sort_values("city_name"),
                x="city_name", y="value", color="age_group",
                barmode="stack",
                title=f"年齢構成別人口（{latest_age_year}年）",
                labels={"city_name": "市名", "value": "人口（人）", "age_group": "年齢区分"},
                color_discrete_sequence=["#2ca02c", "#1f77b4", "#d62728"],
            )
            fig_age.update_layout(
                height=380,
                legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
                margin=dict(l=15, r=15, t=40, b=40),
            )
            st.plotly_chart(fig_age, use_container_width=True)


# ============================================================
# タブ3: 人の移動（地図フローマップ＆転入超過）
# ============================================================
with tab3:
    st.header("🚚 人の移動（地図フローマップ＆転入超過分析）")

    # 1. 地図フローマップ
    st.subheader("1. 🗺️ 市区町村別の人の移動フローマップ（どこから来て、どこへ行くか？）")
    show_guide(
        "地図フローマップの読み解き方",
        "選択した市を中心に、近隣自治体との間で年間何人の移動が発生しているかを地図上に線で描画したものです。",
        "・【青い線】流入元（その市へ引っ越してきた人）\n・【オレンジの線】流出先（その市から引っ越していった人）\n線の太さは人数規模に比例しています。",
        "流入が多い自治体はチラシやWeb広告の重点配信先、流出が多い自治体は競合エリアや顧客奪回対策のヒントになります。"
    )

    map_city_col, map_mode_col, map_top_col = st.columns([2, 3, 2])
    with map_city_col:
        selected_map_city = st.selectbox(
            "中心とする市を選択",
            selected_cities,
            key="map_city_select"
        )
    with map_mode_col:
        flow_display_mode = st.radio(
            "表示する移動",
            ["📥 流入元のみ (どこから?)", "📤 流出先のみ (どこへ?)", "両方を表示"],
            horizontal=True,
            key="flow_display_mode"
        )
    with map_top_col:
        top_n = st.slider("表示件数 (TOP N)", min_value=3, max_value=10, value=5, key="map_top_n")

    if not df_od.empty and selected_map_city:
        city_od_data = df_od[df_od["city_name"] == selected_map_city].copy()
        exclude_partners = ["全国", "愛知県", "北海道", "東京都", "大阪府", "神奈川県", "静岡県", "三重県", "岐阜県"]
        city_od_filtered = city_od_data[~city_od_data["partner_name"].isin(exclude_partners)].copy()

        # 基準市の座標
        center_lat, center_lon = MIGRATION_GEO_COORDS.get(selected_map_city, (34.9892, 136.9984))

        # 流入データ
        inflow_df = city_od_filtered[city_od_filtered["flow_type"] == "転入元（流入元）"].sort_values("persons", ascending=False).head(top_n)
        # 流出データ
        outflow_df = city_od_filtered[city_od_filtered["flow_type"] == "転出先（流出先）"].sort_values("persons", ascending=False).head(top_n)

        # Plotly Mapbox Figure
        fig_map = go.Figure()

        # 最大人数で太さを正規化（2px 〜 7px）
        all_persons = []
        if "流入元" in flow_display_mode or "両方" in flow_display_mode:
            all_persons.extend(inflow_df["persons"].tolist())
        if "流出先" in flow_display_mode or "両方" in flow_display_mode:
            all_persons.extend(outflow_df["persons"].tolist())
        max_p = max(all_persons) if all_persons else 1

        def get_width(p):
            return max(2.0, min(8.0, 2.0 + (p / max_p) * 6.0))

        # 1. 流入元ライン（青）
        if "流入元" in flow_display_mode or "両方" in flow_display_mode:
            for _, row in inflow_df.iterrows():
                p_name = row["partner_name"]
                p_count = row["persons"]
                if p_name in MIGRATION_GEO_COORDS:
                    p_lat, p_lon = MIGRATION_GEO_COORDS[p_name]
                    # 直線
                    fig_map.add_trace(go.Scattermapbox(
                        mode="lines",
                        lon=[p_lon, center_lon],
                        lat=[p_lat, center_lat],
                        line=dict(width=get_width(p_count), color="#1f77b4"),
                        hoverinfo="text",
                        text=f"📥 流入: {p_name} ➔ {selected_map_city} ({p_count:,} 人)",
                        name=f"流入: {p_name}",
                        showlegend=False
                    ))
                    # 相手拠点マーカー
                    fig_map.add_trace(go.Scattermapbox(
                        mode="markers+text",
                        lon=[p_lon],
                        lat=[p_lat],
                        marker=dict(size=10, color="#1f77b4"),
                        text=[f"{p_name}<br>({p_count:,}人)"],
                        textposition="top center",
                        hoverinfo="text",
                        textfont=dict(size=11, color="#1f77b4"),
                        showlegend=False
                    ))

        # 2. 流出先ライン（オレンジ）
        if "流出先" in flow_display_mode or "両方" in flow_display_mode:
            for _, row in outflow_df.iterrows():
                p_name = row["partner_name"]
                p_count = row["persons"]
                if p_name in MIGRATION_GEO_COORDS:
                    p_lat, p_lon = MIGRATION_GEO_COORDS[p_name]
                    fig_map.add_trace(go.Scattermapbox(
                        mode="lines",
                        lon=[center_lon, p_lon],
                        lat=[center_lat, p_lat],
                        line=dict(width=get_width(p_count), color="#ff7f0e"),
                        hoverinfo="text",
                        text=f"📤 流出: {selected_map_city} ➔ {p_name} ({p_count:,} 人)",
                        name=f"流出: {p_name}",
                        showlegend=False
                    ))
                    fig_map.add_trace(go.Scattermapbox(
                        mode="markers+text",
                        lon=[p_lon],
                        lat=[p_lat],
                        marker=dict(size=10, color="#ff7f0e"),
                        text=[f"{p_name}<br>({p_count:,}人)"],
                        textposition="bottom center",
                        hoverinfo="text",
                        textfont=dict(size=11, color="#d95f02"),
                        showlegend=False
                    ))

        # 3. 基準市マーカー（中心・目立つ星型または大きめの赤丸）
        fig_map.add_trace(go.Scattermapbox(
            mode="markers+text",
            lon=[center_lon],
            lat=[center_lat],
            marker=dict(size=16, color="#e41a1c"),
            text=[f"📍 基準: {selected_map_city}"],
            textposition="top right",
            hoverinfo="text",
            textfont=dict(size=13, color="#e41a1c", family="Arial Black"),
            showlegend=False
        ))

        # レイアウト設定
        fig_map.update_layout(
            mapbox=dict(
                style="carto-positron",
                center=dict(lat=center_lat, lon=center_lon),
                zoom=9.8,
            ),
            margin=dict(l=0, r=0, t=20, b=0),
            height=480,
        )
        st.plotly_chart(fig_map, use_container_width=True)

        # ランキング表の並列表示
        st.markdown(f"##### 📊 {selected_map_city} の移動実績数値テーブル（2022年年報）")
        col_tbl_in, col_tbl_out = st.columns(2)
        with col_tbl_in:
            st.markdown(f"**📥 【流入元】{selected_map_city} に引っ越してきた自治体 TOP10**")
            in_full = city_od_filtered[city_od_filtered["flow_type"] == "転入元（流入元）"].sort_values("persons", ascending=False).head(10)
            if not in_full.empty:
                in_tbl = in_full[["partner_name", "persons"]].reset_index(drop=True)
                in_tbl.index = in_tbl.index + 1
                in_tbl.columns = ["転入元自治体", "人数（人）"]
                in_tbl["人数（人）"] = in_tbl["人数（人）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(in_tbl, use_container_width=True)
        with col_tbl_out:
            st.markdown(f"**📤 【流出先】{selected_map_city} から引っ越していった自治体 TOP10**")
            out_full = city_od_filtered[city_od_filtered["flow_type"] == "転出先（流出先）"].sort_values("persons", ascending=False).head(10)
            if not out_full.empty:
                out_tbl = out_full[["partner_name", "persons"]].reset_index(drop=True)
                out_tbl.index = out_tbl.index + 1
                out_tbl.columns = ["転出先自治体", "人数（人）"]
                out_tbl["人数（人）"] = out_tbl["人数（人）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(out_tbl, use_container_width=True)

    st.markdown("---")

    # 2. 転入超過数（純移動数）
    st.subheader("2. 社会増減数（年間 転入超過数 ＝ ネットで何人増えたか？）")
    show_guide(
        "転入超過数（ネット純移動数）の意味",
        "【計算式】転入超過数 ＝ 転入者数（引っ越してきた人） － 転出者数（出ていった人）。年間で他自治体から差し引き何人増減したかを表します。",
        "・プラス（青色） ＝ 人が引き寄せられて純増している『選ばれている街』。\n・マイナス（赤色） ＝ 人が流出している街。\n単なる人口数ではなく、『街の勢い・求心力・住宅需要の流入』を直接表します。",
        "転入超過が続いている市は、賃貸住宅の空室リスクが極めて低く、一次取得（注文・分譲住宅）の顧客が常に新規流入している最優先エリアです。"
    )

    y_min, y_max = year_range_pop
    df_net_mig = filter_df(df_pop, selected_codes, "A1702", y_min, y_max)
    if not df_net_mig.empty:
        fig_net = px.bar(
            df_net_mig.sort_values(["year", "city_name"]),
            x="year", y="value", color="city_name",
            barmode="group",
            title="年間 転入超過数の推移（人/年）",
            labels={"year": "年", "value": "転入超過数（人）", "city_name": "市名"},
            color_discrete_map=CITY_COLORS,
        )
        fig_net.add_hline(y=0, line_dash="dash", line_color="black")
        fig_net.update_layout(
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
            margin=dict(l=15, r=15, t=40, b=40),
            height=380,
        )
        st.plotly_chart(fig_net, use_container_width=True)

        pivot_net = make_pivot_table(df_net_mig)
        st.dataframe(pivot_net.style.format("{:+,.0f}"), use_container_width=True)
        download_button(pivot_net, "net_migration.csv")


# ============================================================
# タブ4: 住宅着工統計
# ============================================================
with tab4:
    st.header("🏗️ 住宅着工統計（利用関係別・床面積）")

    if not df_housing.empty:
        y_min, y_max = year_range_housing

        st.subheader("1. 着工新設住宅 総戸数の推移")
        show_guide(
            "新設住宅着工戸数（合計）",
            "国土交通省『建築着工統計調査』に基づく、その年に工事が始まった新築住宅の総数。",
            "そのエリアで年間どれだけの住宅供給マーケットが存在するかの実寸大。景気・金利・資材価格の影響を直接反映します。",
            "自社の受注シェア（自社年間棟数 ÷ 市の着工数）を測る分母として必須の指標です。"
        )
        df_starts_total = filter_df(df_housing, selected_codes, "H1800", y_min, y_max)
        if not df_starts_total.empty:
            fig = make_bar_chart(df_starts_total, "新設住宅着工戸数（合計）", "戸数")
            st.plotly_chart(fig, use_container_width=True)
            pivot = make_pivot_table(df_starts_total)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "housing_starts_total.csv")

        st.subheader("2. 利用関係別の市場構成（持家・貸家・分譲住宅）")
        show_guide(
            "利用関係別の分類（持家 / 貸家 / 分譲住宅）",
            "①持家＝施主が自分で住む（注文住宅）、②貸家＝他人に貸す目的（アパート・賃貸）、③分譲住宅＝販売目的（建売住宅＋分譲マンション）。",
            "【持家＝注文住宅市場】【貸家＝木造賃貸アパート市場】【分譲住宅＝建売・分譲マンション市場】の勢いを示します。",
            "・持家比率が高い市 ＝ 土地持ち施主や郊外型注文住宅が主戦場。\n・貸家が多い市 ＝ 相続税対策・資産運用アパートの提案適地。\n・分譲が急増している市 ＝ 注文から建売に流れているエリア。建売分譲用地の仕入れターゲット。"
        )

        detail_city = st.selectbox(
            "内訳を詳しく見る市を選択してください",
            selected_cities,
            key="detail_city_starts"
        )
        detail_code = CITY_NAMES.get(detail_city, "")

        if detail_code:
            type_codes = {"H1801": "持家(注文住宅)", "H1802": "貸家(アパート等)", "H1803": "分譲住宅(建売＋マンション)"}
            df_by_type = filter_df_multi(
                df_housing, [detail_code], list(type_codes.keys()), y_min, y_max
            )
            if not df_by_type.empty:
                df_by_type["type"] = df_by_type["indicator_code"].map(type_codes)
                fig_type = px.bar(
                    df_by_type.sort_values("year"),
                    x="year", y="value", color="type",
                    barmode="stack",
                    title=f"{detail_city}：利用関係別の着工戸数推移",
                    labels={"year": "年", "value": "戸数", "type": "利用関係"},
                    color_discrete_map={"持家(注文住宅)": "#1f77b4", "貸家(アパート等)": "#ff7f0e", "分譲住宅(建売＋マンション)": "#2ca02c"},
                )
                fig_type.update_layout(
                    height=380,
                    legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
                    margin=dict(l=15, r=15, t=40, b=40),
                )
                st.plotly_chart(fig_type, use_container_width=True)

                pivot_type = df_by_type.pivot_table(
                    values="value", index="year", columns="type", aggfunc="first"
                ).sort_index(ascending=False)
                st.dataframe(pivot_type.style.format("{:,.0f}"), use_container_width=True)
                download_button(pivot_type, f"housing_starts_{detail_city}.csv")

        st.subheader("3. 🏢 貸家（アパート・賃貸）着工戸数の市間比較")
        df_kashiya = filter_df(df_housing, selected_codes, "H1802", y_min, y_max)
        if not df_kashiya.empty:
            fig = make_line_chart(df_kashiya, "貸家着工戸数の推移", "戸数")
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("4. 🏡 持家（注文）および分譲住宅の市間比較")
        df_mochiya = filter_df(df_housing, selected_codes, "H1801", y_min, y_max)
        if not df_mochiya.empty:
            fig_m = make_line_chart(df_mochiya, "持家（注文住宅）着工戸数の推移", "戸数")
            st.plotly_chart(fig_m, use_container_width=True)

        df_bunjou = filter_df(df_housing, selected_codes, "H1803", y_min, y_max)
        if not df_bunjou.empty:
            fig_b = make_line_chart(df_bunjou, "分譲住宅（建売＋マンション）着工戸数の推移", "戸数")
            st.plotly_chart(fig_b, use_container_width=True)


# ============================================================
# タブ5: 住宅ストック・空き家
# ============================================================
with tab5:
    st.header("🏘️ 住宅ストック・空き家（リフォーム需要）")

    if not df_housing.empty:
        st.subheader("1. 住宅ストック総数と空き家の推移")
        show_guide(
            "総住宅数・空き家数",
            "総務省『住宅・土地統計調査』（5年周期）に基づく既存住宅の現存戸数および空き家数。",
            "新築着工が減ってもストック総数は増えており、住宅事業の主戦場が『新築』から『維持・リフォーム』に移っている実態を示します。",
            "空き家数が多い市は『中古住宅の買取再販』や『空き家解体後の分譲地化』『古民家リノベ』のターゲットです。"
        )

        col_st1, col_st2 = st.columns(2)
        with col_st1:
            df_stock = filter_df(df_housing, selected_codes, "H1100", 1980, 2025)
            if not df_stock.empty:
                fig = make_bar_chart(df_stock, "総住宅数の推移（戸）", "戸数")
                st.plotly_chart(fig, use_container_width=True)

        with col_st2:
            df_vacant = filter_df(df_housing, selected_codes, "H110202", 1980, 2025)
            if not df_vacant.empty:
                fig = make_bar_chart(df_vacant, "空き家数の推移（戸）", "戸数")
                st.plotly_chart(fig, use_container_width=True)

        st.subheader("2. 木造 vs 非木造住宅ストック")
        detail_city2 = st.selectbox(
            "構造別内訳を見る市を選択してください",
            selected_cities,
            key="detail_city_stock"
        )
        detail_code2 = CITY_NAMES.get(detail_city2, "")

        if detail_code2:
            struct_codes = {"H1501": "木造", "H1502": "非木造"}
            df_struct = filter_df_multi(df_housing, [detail_code2], list(struct_codes.keys()), 1980, 2025)
            if not df_struct.empty:
                df_struct["structure"] = df_struct["indicator_code"].map(struct_codes)
                fig_struct = px.bar(
                    df_struct.sort_values("year"),
                    x="year", y="value", color="structure",
                    barmode="stack",
                    title=f"{detail_city2}：木造/非木造住宅数の推移",
                    labels={"year": "年", "value": "住宅数（戸）", "structure": "構造"},
                    color_discrete_map={"木造": "#8c564b", "非木造": "#7f7f7f"},
                )
                fig_struct.update_layout(
                    height=380,
                    legend=dict(orientation="h", yanchor="top", y=-0.25, xanchor="center", x=0.5),
                    margin=dict(l=15, r=15, t=40, b=40),
                )
                st.plotly_chart(fig_struct, use_container_width=True)

        st.subheader("3. 🏚️ 築年数別住宅数（リフォーム潜在市場規模）")
        show_guide(
            "建築時期別住宅数",
            "いつ建てられた家が現存しているかの内訳（住宅・土地統計調査）。",
            "『築15〜20年＝外壁塗装・給湯器』『築25〜35年＝水回り刷新・フルリフォーム』『築40年以上＝耐震改修・建て替え』の周期を迎えます。",
            "2000年以前（築25年以上）の住宅ストックが大量に存在する市は、リフォーム事業のチラシ投函・OB顧客掘り起こし・イベント開催の最重点エリアです。"
        )

        detail_city3 = st.selectbox(
            "築年数内訳を見る市を選択してください",
            selected_cities,
            key="detail_city_age"
        )
        detail_code3 = CITY_NAMES.get(detail_city3, "")

        if detail_code3:
            age_codes_map = {
                "H1615": "～1960年(築60年超)",
                "H1612": "1971～1980年(旧耐震)",
                "H1613": "1981～1990年(築35年前後)",
                "H1619": "1991～2000年(築25年前後)",
                "H1620": "2001～2005年(築20年前後)",
                "H1622": "2006～2010年",
                "H1624": "2011～2015年",
                "H1626": "2016～2020年",
                "H1627": "2021～2023年",
            }
            df_build_age = filter_df_multi(
                df_housing, [detail_code3], list(age_codes_map.keys()), 1980, 2025
            )
            if not df_build_age.empty:
                df_build_age["year_int"] = df_build_age["year"].astype(int)
                latest = df_build_age["year_int"].max()
                df_build_latest = df_build_age[df_build_age["year_int"] == latest].copy()
                df_build_latest["period"] = df_build_latest["indicator_code"].map(age_codes_map)

                if not df_build_latest.empty:
                    period_order = list(age_codes_map.values())
                    df_build_latest["period"] = pd.Categorical(
                        df_build_latest["period"], categories=period_order, ordered=True
                    )
                    df_build_latest = df_build_latest.sort_values("period")

                    fig_age = px.bar(
                        df_build_latest,
                        x="period", y="value",
                        title=f"{detail_city3}：建築時期別ストック量（{latest}年時点）",
                        labels={"period": "建築時期", "value": "戸数"},
                        color_discrete_sequence=["#e377c2"],
                    )
                    fig_age.update_layout(
                        height=380,
                        margin=dict(l=15, r=15, t=40, b=80),
                        xaxis_tickangle=-45
                    )
                    st.plotly_chart(fig_age, use_container_width=True)


# ============================================================
# タブ6: 初心者向け 指標解説ガイド
# ============================================================
with tab6:
    st.header("📖 住宅・不動産マーケティング指標の読み解きガイド")
    st.markdown(
        """
        社内メンバー（営業・設計・企画等）が会議や戦略立案でデータを正しく活用できるようにするための用語解説集です。
        """
    )

    with st.container():
        st.markdown("### 1. 人口・世帯構造から何を読み取るか？")
        st.markdown(
            """
            - **総人口 vs 世帯数**
              - **基本原則:** 家を建てたり借りたりするのは「人」ではなく「世帯」です。
              - 人口が減っていても、核家族化・単身世帯の増加で**「世帯数が増加している市」は住宅需要が維持されます**。
            - **単身世帯（一人暮らし） vs 核家族世帯（ファミリー）**
              - 単身世帯の急増エリア ＝ **木造賃貸アパート（ワンルーム〜1LDK）の最適地**。
              - 核家族世帯が多いエリア ＝ **注文住宅・建売分譲住宅のメインターゲット**。
            - **持ち家世帯 vs 借家世帯（現住居の所有形態）**
              - **持ち家世帯:** リフォーム・外壁塗装・建て替え・相続アパート建築の対象。
              - **借家（賃貸）世帯:** **将来の家づくり（注文・建売購入）の最有力見込み客**。この世帯が多い市ほど新築集客が効きます。
            """
        )

        st.markdown("---")
        st.markdown("### 2. 人の移動（転入超過・流入元・流出先）")
        st.markdown(
            """
            - **転入超過数（純増数）**
              - `転入者数 － 転出者数`。プラスなら人口が他市から純流入、マイナスなら流出。
              - 転入超過の市はアパートの空室リスクが低く、一次取得層が絶えず集まっています。
            - **流入元・流出先（ODデータ）**
              - 例: 「岡崎市に転入してくる人の多くは豊田市・安城市・名古屋市から来ている」と分かれば、展示場来場やWeb広告の配信エリアをどこに広げるべきかが明確になります。
            """
        )

        st.markdown("---")
        st.markdown("### 3. 住宅着工統計（利用関係別）で自社の攻め時を知る")
        st.markdown(
            """
            | 統計用語 | 業界での通称 | 正式な内訳と事業における意味合い |
            | :--- | :--- | :--- |
            | **持家（もちいえ）** | **注文住宅** | 施主が所有地または新規購入地に自分で住む家を建てる。地主層・建替え層が多く、粗利率・顧客単価が高い。 |
            | **貸家（かしや）** | **アパート・賃貸** | **木造賃貸アパート等の市場規模**。節税対策や遊休地活用。急増している市は地主営業の好機。 |
            | **分譲住宅（ぶんじょう）** | **建売 ＋ マンション** | **『建売一戸建て住宅』と『分譲マンション』の合算値**。土地価格高騰時に注文から流れる層の受け皿。 |
            """
        )


# ============================================================
# フッター
# ============================================================

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.85em;">
        📊 商圏エリアデータダッシュボード v1.4（地図フローマップ実装版）<br>
        データ出典: <a href="https://www.e-stat.go.jp/" target="_blank">e-Stat（政府統計の総合窓口）</a>
        ・社会・人口統計体系 / 建築着工統計調査 / 住民基本台帳人口移動報告（2022年）
    </div>
    """,
    unsafe_allow_html=True,
)
