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

# モバイル対応カスタムCSS
st.markdown(
    """
    <style>
    /* モバイルでのフォントサイズ・パディング調整 */
    @media (max-width: 768px) {
        .block-container {
            padding-top: 1.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        h1 {
            font-size: 1.5rem !important;
        }
        h2 {
            font-size: 1.25rem !important;
        }
        h3 {
            font-size: 1.1rem !important;
        }
        .stMetric {
            padding: 8px !important;
        }
    }
    /* 解説ボックスのスタイル */
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
    """簡易パスワード保護"""
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
    """CSVファイルからデータを読み込む"""
    pop_path = os.path.join(DATA_DIR, "population.csv")
    housing_path = os.path.join(DATA_DIR, "housing.csv")
    indicators_path = os.path.join(DATA_DIR, "housing_indicators.csv")

    dfs = {}
    for name, path in [("population", pop_path), ("housing", housing_path), ("indicators", indicators_path)]:
        if os.path.exists(path):
            df = pd.read_csv(path, dtype={"city_code": str, "year": str})
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df["year"] = df["year"].astype(str)
            dfs[name] = df
        else:
            st.warning(f"⚠️ データファイルが見つかりません: {path}")
            dfs[name] = pd.DataFrame()

    return dfs


data = load_data()
df_pop = data["population"]
df_housing = data["housing"]
df_indicators = data["indicators"]

# ============================================================
# 市の定義
# ============================================================

CITIES = {
    "23202": {"name": "岡崎市", "area": "西三河"},
    "23209": {"name": "碧南市", "area": "西三河"},
    "23210": {"name": "刈谷市", "area": "西三河"},
    "23211": {"name": "豊田市", "area": "西三河"},
    "23212": {"name": "安城市", "area": "西三河"},
    "23213": {"name": "西尾市", "area": "西三河"},
    "23222": {"name": "東海市", "area": "知多"},
    "23223": {"name": "大府市", "area": "知多"},
    "23224": {"name": "知多市", "area": "知多"},
    "23225": {"name": "知立市", "area": "西三河"},
    "23227": {"name": "高浜市", "area": "西三河"},
}

CITY_NAMES = {v["name"]: k for k, v in CITIES.items()}
ALL_CITY_NAMES = [CITIES[k]["name"] for k in sorted(CITIES.keys())]

# カラーパレット
CITY_COLORS = {
    "岡崎市": "#1f77b4", "碧南市": "#aec7e8", "刈谷市": "#ff7f0e",
    "豊田市": "#ffbb78", "安城市": "#2ca02c", "西尾市": "#98df8a",
    "東海市": "#d62728", "大府市": "#ff9896", "知多市": "#9467bd",
    "知立市": "#c5b0d5", "高浜市": "#8c564b",
}

# ============================================================
# サイドバー（全選択・全解除ボタン付き）
# ============================================================

with st.sidebar:
    st.markdown("## 🏠 商圏エリアダッシュボード")
    st.markdown("**愛知県11市** の市場データ分析ツール")
    st.markdown("---")

    # エリアフィルター
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

    # 全選択・全解除ボタン用のセッションステート初期化
    if "selected_cities" not in st.session_state:
        st.session_state["selected_cities"] = available_cities
    else:
        # エリアフィルターが変わった場合、存在しない市を除外
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
    # セッションステート同期
    st.session_state["selected_cities"] = selected_cities

    st.markdown("---")
    st.markdown("### 📊 表示期間の設定")

    year_range_pop = st.slider(
        "人口データの年範囲",
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
    st.caption("社会・人口統計体系 市区町村データ")


selected_codes = [CITY_NAMES[name] for name in selected_cities if name in CITY_NAMES]

if not selected_codes:
    st.warning("⚠️ サイドバーから対象市を1つ以上選択してください。（「全選択」ボタンで一括選択できます）")
    st.stop()


# ============================================================
# 解説コンポーネント関数
# ============================================================

def show_guide(title, rule, meaning, business_point):
    """各指標の集計ルールと読み解き方を初心者向けに表示する"""
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
# グラフ描画ヘルパー関数（モバイル最適化）
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

# タブ構成
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 概要・KPI",
    "👥 人口・世帯",
    "🏗️ 住宅着工統計",
    "🏘️ 住宅ストック・空き家",
    "📖 指標解説ガイド",
])

# ============================================================
# タブ1: 概要・KPI
# ============================================================
with tab1:
    st.header("📋 商圏サマリー・最新ランキング")
    
    show_guide(
        "商圏サマリーとKPIの見方",
        "最新年次（人口は国勢調査年、着工は直近期）の各市数値を合算・ランキング化したものです。",
        "選択した市全体の市場規模感（総人口・年間着工総数）と、どの自治体が商圏内で最大のボリュームを持っているかが一目で分かります。",
        "着工戸数上位の市は『シェア拡大・主力営業エリア』、人口が増加している市は『木造賃貸や分譲の新規開拓エリア』としてリソース配分を検討できます。"
    )

    if not df_pop.empty and not df_housing.empty:
        # 最新年の人口データ
        latest_pop = df_pop[
            (df_pop["city_code"].isin(selected_codes))
            & (df_pop["indicator_code"] == "A1101")
        ].copy()
        if not latest_pop.empty:
            latest_pop["year_int"] = latest_pop["year"].astype(int)
            latest_year = latest_pop["year_int"].max()
            latest_pop = latest_pop[latest_pop["year_int"] == latest_year]

        # 最新年の着工データ
        latest_starts = df_housing[
            (df_housing["city_code"].isin(selected_codes))
            & (df_housing["indicator_code"] == "H1800")
        ].copy()
        if not latest_starts.empty:
            latest_starts["year_int"] = latest_starts["year"].astype(int)
            latest_starts_year = latest_starts["year_int"].max()
            latest_starts = latest_starts[latest_starts["year_int"] == latest_starts_year]

        # KPIカード（モバイルでも見やすい2列×2行構成）
        kpi_col1, kpi_col2 = st.columns(2)
        with kpi_col1:
            if not latest_pop.empty:
                total_pop = latest_pop["value"].sum()
                st.metric("総人口（選択市合計）", f"{total_pop:,.0f} 人", help=f"{latest_year}年時点の国勢調査人口")
        with kpi_col2:
            if not latest_starts.empty:
                total_starts = latest_starts["value"].sum()
                st.metric("年間着工戸数（合計）", f"{total_starts:,.0f} 戸", help=f"{latest_starts_year}年 新設住宅着工総数")

        kpi_col3, kpi_col4 = st.columns(2)
        with kpi_col3:
            if not latest_starts.empty:
                latest_kashiya = df_housing[
                    (df_housing["city_code"].isin(selected_codes))
                    & (df_housing["indicator_code"] == "H1802")
                ].copy()
                latest_kashiya["year_int"] = latest_kashiya["year"].astype(int)
                latest_kashiya = latest_kashiya[latest_kashiya["year_int"] == latest_starts_year]
                total_kashiya = latest_kashiya["value"].sum()
                st.metric("貸家着工（賃貸市場）", f"{total_kashiya:,.0f} 戸", help=f"{latest_starts_year}年 アパート等の着工数")
        with kpi_col4:
            if not latest_starts.empty:
                latest_bunjou = df_housing[
                    (df_housing["city_code"].isin(selected_codes))
                    & (df_housing["indicator_code"] == "H1803")
                ].copy()
                latest_bunjou["year_int"] = latest_bunjou["year"].astype(int)
                latest_bunjou = latest_bunjou[latest_bunjou["year_int"] == latest_starts_year]
                total_bunjou = latest_bunjou["value"].sum()
                st.metric("分譲着工（建売・マンション）", f"{total_bunjou:,.0f} 戸", help=f"{latest_starts_year}年 分譲住宅着工数")

        st.markdown("---")

        # ランキング表示
        st.subheader("🏆 商圏内ランキング比較")
        rank_col1, rank_col2 = st.columns(2)

        with rank_col1:
            st.markdown(f"**人口規模ランキング（{latest_year}年）**")
            if not latest_pop.empty:
                rank_pop = latest_pop[["city_name", "value"]].sort_values("value", ascending=False).reset_index(drop=True)
                rank_pop.index = rank_pop.index + 1
                rank_pop.columns = ["市名", "人口（人）"]
                rank_pop["人口（人）"] = rank_pop["人口（人）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(rank_pop, use_container_width=True)

        with rank_col2:
            st.markdown(f"**新設住宅着工戸数ランキング（{latest_starts_year}年）**")
            if not latest_starts.empty:
                rank_starts = latest_starts[["city_name", "value"]].sort_values("value", ascending=False).reset_index(drop=True)
                rank_starts.index = rank_starts.index + 1
                rank_starts.columns = ["市名", "着工数（戸）"]
                rank_starts["着工数（戸）"] = rank_starts["着工数（戸）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(rank_starts, use_container_width=True)

        # シェア円グラフ
        st.subheader(f"📊 着工新設住宅の商圏シェア（{latest_starts_year}年）")
        if not latest_starts.empty:
            fig_share = px.pie(
                latest_starts, values="value", names="city_name",
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
# タブ2: 人口・世帯
# ============================================================
with tab2:
    st.header("👥 人口・世帯トレンド")

    if not df_pop.empty:
        y_min, y_max = year_range_pop

        # 1. 総人口推移
        st.subheader("1. 総人口の推移")
        show_guide(
            "総人口の推移",
            "総務省「国勢調査」および「人口推計」に基づく各市町村の人口実数。",
            "自治体の長期的な成長・衰退傾向。人口が増加している市は、住宅・建築市場全体の需要パイが維持・拡大しています。",
            "人口増加市（または減少が緩やかな市）は、注文住宅の一次取得層や賃貸需要が長期的に期待できる最優先エリアです。"
        )
        df_total_pop = filter_df(df_pop, selected_codes, "A1101", y_min, y_max)
        if not df_total_pop.empty:
            fig = make_line_chart(df_total_pop, "総人口の推移（人）", "人口（人）")
            st.plotly_chart(fig, use_container_width=True)
            pivot = make_pivot_table(df_total_pop)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "population_total.csv")

        # 2. 世帯数推移
        st.subheader("2. 世帯数の推移")
        show_guide(
            "世帯数の推移",
            "一般世帯＋施設等の世帯数の合計。",
            "【最重要】人口が横ばい・減少していても、世帯数が増加しているケースが多々あります（単身化・核家族化）。住宅需要は『人頭』ではなく『世帯単位』で発生するため、世帯数が増えている間は住居需要が旺盛です。",
            "世帯数増加率が高いエリアは、木造賃貸アパート（単身〜2人向け）やコンパクト分譲住宅の強い引き合いが見込めます。"
        )
        df_households = filter_df(df_pop, selected_codes, "A1500", y_min, y_max)
        if not df_households.empty:
            fig = make_line_chart(df_households, "世帯数の推移（世帯）", "世帯数")
            st.plotly_chart(fig, use_container_width=True)
            pivot = make_pivot_table(df_households)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "households.csv")

        # 3. 年齢3区分構成
        st.subheader("3. 年齢階級別の人口構成")
        show_guide(
            "年齢3区分の比率（年少・生産年齢・老年）",
            "15歳未満（年少＝子ども）、15〜64歳（生産年齢＝働き盛り）、65歳以上（老年＝シニア）。",
            "年少人口が多い市は子育てファミリーが多く注文住宅需要が強い。高齢者比率が高い市は既存住宅のリフォームや相続・建て替え需要が厚い。",
            "子育て層が多い市は『注文・分譲住宅』、シニア比率が高い市は『断熱・バリアフリーリフォーム』や『木造賃貸アパートによる遊休地活用提案』が刺さります。"
        )
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

        # 4. 転入・転出（社会増減）
        st.subheader("4. 転入・転出（人の流入と流出）")
        show_guide(
            "転入者数・転出者数（社会移動）",
            "住民基本台帳に基づく他市区町村からの転入および他市区町村への転出者数。",
            "『転入 ＞ 転出（転入超過）』であれば、雇用の強さや住環境の良さで周辺から人を引きつけている証拠。賃貸の空室率が低く、将来の住宅購入見込み客が常に流入しています。",
            "転入超過エリアは賃貸アパート経営の安全性が高く、地主様へのアパート建築提案で強い説得材料になります。"
        )
        col_in, col_out = st.columns(2)
        with col_in:
            df_in = filter_df(df_pop, selected_codes, "A1700", y_min, y_max)
            if not df_in.empty:
                fig = make_line_chart(df_in, "転入者数（人）", "人数（人）")
                st.plotly_chart(fig, use_container_width=True)
        with col_out:
            df_out = filter_df(df_pop, selected_codes, "A1701", y_min, y_max)
            if not df_out.empty:
                fig = make_line_chart(df_out, "転出者数（人）", "人数（人）")
                st.plotly_chart(fig, use_container_width=True)


# ============================================================
# タブ3: 住宅着工統計
# ============================================================
with tab3:
    st.header("🏗️ 住宅着工統計（利用関係別・床面積）")

    if not df_housing.empty:
        y_min, y_max = year_range_housing

        # 着工戸数（合計）
        st.subheader("1. 着工新設住宅 総戸数の推移")
        show_guide(
            "新設住宅着工戸数（合計）",
            "国土交通省『建築着工統計調査』に基づく、その年に新たに建築工事が始まった住宅の戸数。",
            "そのエリアで年間どれだけの住宅供給マーケットが存在するかの実寸大。景気・金利・資材価格の影響を直接反映します。",
            "全体の波を把握しつつ、自社の受注シェア（自社年間棟数 ÷ 市の着工数）を測る分母として必須の指標です。"
        )
        df_starts_total = filter_df(df_housing, selected_codes, "H1800", y_min, y_max)
        if not df_starts_total.empty:
            fig = make_bar_chart(df_starts_total, "新設住宅着工戸数（合計）", "戸数")
            st.plotly_chart(fig, use_container_width=True)
            pivot = make_pivot_table(df_starts_total)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "housing_starts_total.csv")

        # 利用関係別 内訳
        st.subheader("2. 利用関係別の市場構成（持家・貸家・分譲）")
        show_guide(
            "利用関係別の分類（持家 / 貸家 / 分譲）",
            "建築主と住宅の関係性による分類。①持家＝建築主が自分で住む、②貸家＝他人に貸す目的、③分譲＝販売目的（建売・マンション）。",
            "【持家＝注文住宅市場】【貸家＝木造賃貸アパート・賃貸マンション市場】【分譲＝建売住宅・分譲マンション市場】のそれぞれの市場規模と勢いを示します。",
            "・持家比率が高い市 ＝ 土地持ち施主や郊外型注文住宅が主戦場。\n・貸家が多い市 ＝ 相続税対策・資産運用アパートの提案適地。\n・分譲が急増している市 ＝ 土地価格高騰で注文住宅から建売に流れているエリア。建売分譲用地の仕入れターゲット。"
        )

        detail_city = st.selectbox(
            "内訳を詳しく見る市を選択してください",
            selected_cities,
            key="detail_city_starts"
        )
        detail_code = CITY_NAMES.get(detail_city, "")

        if detail_code:
            type_codes = {"H1801": "持家(注文住宅)", "H1802": "貸家(アパート等)", "H1803": "分譲(建売等)"}
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
                    color_discrete_map={"持家(注文住宅)": "#1f77b4", "貸家(アパート等)": "#ff7f0e", "分譲(建売等)": "#2ca02c"},
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

        # 3. 貸家着工の市間比較（賃貸アパート強化）
        st.subheader("3. 🏢 貸家（アパート・賃貸）着工戸数の市間比較")
        show_guide(
            "貸家着工戸数の比較",
            "新たに建設されたアパート・賃貸住宅の戸数。",
            "どの市町村でアパート建築が活発に行われているか。企業の工場・オフィス新設や駅前再開発に連動して急増する傾向があります。",
            "新規事業『木造賃貸住宅（アパート）』の営業リソースを最優先で集中させるべきエリア選定の最重要データです。"
        )
        df_kashiya = filter_df(df_housing, selected_codes, "H1802", y_min, y_max)
        if not df_kashiya.empty:
            fig = make_line_chart(df_kashiya, "貸家着工戸数の推移", "戸数")
            st.plotly_chart(fig, use_container_width=True)

        # 4. 持家・分譲着工
        st.subheader("4. 🏡 持家（注文）および分譲（建売）の市間比較")
        df_mochiya = filter_df(df_housing, selected_codes, "H1801", y_min, y_max)
        if not df_mochiya.empty:
            fig_m = make_line_chart(df_mochiya, "持家（注文住宅）着工戸数の推移", "戸数")
            st.plotly_chart(fig_m, use_container_width=True)

        df_bunjou = filter_df(df_housing, selected_codes, "H1803", y_min, y_max)
        if not df_bunjou.empty:
            fig_b = make_line_chart(df_bunjou, "分譲住宅着工戸数の推移", "戸数")
            st.plotly_chart(fig_b, use_container_width=True)


# ============================================================
# タブ4: 住宅ストック・空き家
# ============================================================
with tab4:
    st.header("🏘️ 住宅ストック・空き家（リフォーム需要）")

    if not df_housing.empty:
        # 総住宅数と空き家
        st.subheader("1. 住宅ストック総数と空き家の推移")
        show_guide(
            "総住宅数・空き家数",
            "総務省『住宅・土地統計調査』（5年周期）に基づく既存住宅の現存戸数および空き家数。",
            "過去に建てられた住宅の蓄積量。新築着工が減ってもストック総数は増えており、住宅事業の主戦場が『新築』から『維持・リフォーム』に移っている実態を示します。",
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

        # 木造 vs 非木造
        st.subheader("2. 木造 vs 非木造住宅ストック")
        show_guide(
            "木造住宅と非木造住宅の数",
            "建物の骨組みによる分類。木造（在来工法・ツーバイフォー等）と非木造（鉄骨・RC・SRC等）。",
            "地域の『木の家親和性』。愛知県三河地域は伝統的に木造戸建て比率が極めて高く、木造の技術力や耐震性能への関心が高い市場です。",
            "木造比率の高いエリアは自社の木造建築ノウハウ（木造注文・木造アパート・木造リフォーム）がストレートに響きます。"
        )

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

        # 築年数別ストック
        st.subheader("3. 🏚️ 築年数別住宅数（リフォーム潜在市場規模）")
        show_guide(
            "建築時期別住宅数",
            "いつ建てられた家が現存しているかの内訳（住宅・土地統計調査）。",
            "【リフォーム需要の宝庫】一般に『築15〜20年＝外壁屋根塗装・給湯器交換』『築25〜35年＝水回り刷新・フルリフォーム』『築40年以上＝耐震改修・建て替え』の周期を迎えます。",
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
# タブ5: 初心者向け 指標解説ガイド
# ============================================================
with tab5:
    st.header("📖 住宅・不動産マーケティング指標の読み解きガイド")
    st.markdown(
        """
        社内メンバー（営業・設計・企画等）が会議や戦略立案でデータを正しく活用できるようにするための用語解説集です。
        """
    )

    with st.container():
        st.markdown("### 1. 人口・世帯データから何を読み取るか？")
        st.markdown(
            """
            - **総人口 vs 世帯数**
              - **基本原則:** 家を建てたり借りたりするのは「人」ではなく「世帯」です。
              - 人口が減っていても、核家族化・単身世帯の増加で**「世帯数が増加している市」は住宅需要が維持されます**。
            - **年齢3区分（子ども・現役世代・シニア）**
              - **15歳未満比率が高い市:** 30代〜40代の子育て一次取得層が集まるエリア ＝ **注文住宅・分譲住宅**の最重点商圏。
              - **65歳以上比率が高い市:** 持ち家率が高く住み替えや建て替えが進まないエリア ＝ **フルリフォーム・減築・外壁塗装・バリアフリー**の提案が刺さる商圏。
            - **社会増減（転入 － 転出）**
              - 転入超過の市は、雇用や生活利便性が高く選ばれている街。賃貸アパートの入居率が高く保ちやすいです。
            """
        )

        st.markdown("---")
        st.markdown("### 2. 住宅着工統計（利用関係別）で自社の攻め時を知る")
        st.markdown(
            """
            | 統計用語 | 業界での通称 | 事業における意味合い・営業アクション |
            | :--- | :--- | :--- |
            | **持家（もちいえ）** | **注文住宅** | 施主が土地に自分の家を建てる。地主層・建替え層が多く、粗利率・顧客単価が高い。 |
            | **貸家（かしや）** | **アパート・賃貸** | **木造賃貸アパート等の市場規模**。節税対策や遊休地活用。急増している市は地主営業の好機。 |
            | **分譲住宅（ぶんじょう）** | **建売・分譲マンション** | 土地と建物をセットで販売。土地高騰時に注文から流れる層の受け皿。土地仕入れの目安。 |
            """
        )

        st.markdown("---")
        st.markdown("### 3. リフォーム・非住宅強化へのヒント")
        st.markdown(
            """
            - **リフォームの狙い目（築20年以上のストック量）**
              - 築20〜35年の住宅が多い自治体ほど、外壁塗装・屋根葺き替え・水回り設備刷新（キッチン・風呂）・断熱改修の潜在顧客が密集しています。
            - **木造比率の高さ**
              - 西三河・知多エリアは全国的にも木造住宅の比率が極めて高く、木造建築に対する信頼が厚い土壌があります。新たに展開する「木造賃貸住宅（アパート）」や「木造非住宅建築（店舗・福祉施設・事務所）」でも木造のコスト・工期・減価償却メリットをアピールしやすい商圏です。
            """
        )


# ============================================================
# フッター
# ============================================================

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.85em;">
        📊 商圏エリアデータダッシュボード v1.1（UX改善＆解説強化版）<br>
        データ出典: <a href="https://www.e-stat.go.jp/" target="_blank">e-Stat（政府統計の総合窓口）</a>
        ・社会・人口統計体系 市区町村データ
    </div>
    """,
    unsafe_allow_html=True,
)
