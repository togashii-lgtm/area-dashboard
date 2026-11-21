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
# ページ設定
# ============================================================

st.set_page_config(
    page_title="商圏エリアデータダッシュボード",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# パスワード認証
# ============================================================

def check_password():
    """簡易パスワード保護"""
    # Streamlit Cloud: st.secrets["password"] を使用
    # ローカル: .streamlit/secrets.toml に password = "xxx" を設定
    try:
        correct_password = st.secrets["password"]
    except (FileNotFoundError, KeyError):
        # secrets未設定の場合はスキップ（ローカル開発時）
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
AREA_COLORS = {
    "西三河": "#1f77b4",
    "知多": "#ff7f0e",
}

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

    # エリアフィルター
    area_filter = st.multiselect(
        "エリアで絞り込み",
        ["西三河", "知多"],
        default=["西三河", "知多"],
    )

    # エリアに基づく市リスト
    available_cities = [
        CITIES[k]["name"]
        for k in sorted(CITIES.keys())
        if CITIES[k]["area"] in area_filter
    ]

    selected_cities = st.multiselect(
        "対象市を選択",
        available_cities,
        default=available_cities,
    )

    st.markdown("---")
    st.markdown("### 📊 表示設定")

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


# 選択した市のコードリスト
selected_codes = [CITY_NAMES[name] for name in selected_cities if name in CITY_NAMES]

if not selected_codes:
    st.warning("サイドバーから対象市を1つ以上選択してください。")
    st.stop()


# ============================================================
# ヘルパー関数
# ============================================================

def filter_df(df, codes, indicator_code, year_min, year_max):
    """データフレームを市コード・指標・年でフィルタ"""
    mask = (
        df["city_code"].isin(codes)
        & (df["indicator_code"] == indicator_code)
        & (df["year"].astype(int) >= year_min)
        & (df["year"].astype(int) <= year_max)
    )
    return df[mask].copy()


def filter_df_multi(df, codes, indicator_codes, year_min, year_max):
    """複数指標でフィルタ"""
    mask = (
        df["city_code"].isin(codes)
        & (df["indicator_code"].isin(indicator_codes))
        & (df["year"].astype(int) >= year_min)
        & (df["year"].astype(int) <= year_max)
    )
    return df[mask].copy()


def make_line_chart(df, title, y_label="値", color_col="city_name"):
    """折れ線グラフを作成"""
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
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        height=450,
    )
    return fig


def make_bar_chart(df, title, y_label="値", color_col="city_name", barmode="group"):
    """棒グラフを作成"""
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
        legend=dict(orientation="h", yanchor="bottom", y=-0.3),
        height=450,
    )
    return fig


def make_pivot_table(df, value_col="value", index_col="year", columns_col="city_name"):
    """ピボットテーブルを作成"""
    if df.empty:
        return pd.DataFrame()
    pivot = df.pivot_table(
        values=value_col, index=index_col, columns=columns_col, aggfunc="first"
    )
    pivot = pivot.sort_index(ascending=False)
    return pivot


def download_button(df, filename, label="📥 CSVダウンロード"):
    """CSVダウンロードボタン"""
    csv_data = df.to_csv(index=True, encoding="utf-8-sig")
    st.download_button(
        label=label,
        data=csv_data,
        file_name=filename,
        mime="text/csv",
    )


# ============================================================
# メインコンテンツ
# ============================================================

st.title("🏠 商圏エリアデータダッシュボード")
st.markdown(f"**選択中:** {', '.join(selected_cities)}（{len(selected_cities)}市）")

# タブ構成
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📋 概要・ランキング",
    "👥 人口・世帯",
    "🏗️ 住宅着工統計",
    "🏘️ 住宅ストック",
    "📊 指標比較",
])

# ============================================================
# タブ1: 概要・ランキング
# ============================================================
with tab1:
    st.header("概要・ランキング")

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

        # KPIカード
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if not latest_pop.empty:
                total_pop = latest_pop["value"].sum()
                st.metric("総人口（11市合計）", f"{total_pop:,.0f} 人", help=f"{latest_year}年時点")
        with col2:
            if not latest_starts.empty:
                total_starts = latest_starts["value"].sum()
                st.metric("年間着工戸数（合計）", f"{total_starts:,.0f} 戸", help=f"{latest_starts_year}年")
        with col3:
            if not latest_starts.empty:
                # 貸家着工
                latest_kashiya = df_housing[
                    (df_housing["city_code"].isin(selected_codes))
                    & (df_housing["indicator_code"] == "H1802")
                ].copy()
                latest_kashiya["year_int"] = latest_kashiya["year"].astype(int)
                latest_kashiya = latest_kashiya[latest_kashiya["year_int"] == latest_starts_year]
                total_kashiya = latest_kashiya["value"].sum()
                st.metric("貸家着工（合計）", f"{total_kashiya:,.0f} 戸", help=f"{latest_starts_year}年")
        with col4:
            if not latest_starts.empty:
                latest_bunjou = df_housing[
                    (df_housing["city_code"].isin(selected_codes))
                    & (df_housing["indicator_code"] == "H1803")
                ].copy()
                latest_bunjou["year_int"] = latest_bunjou["year"].astype(int)
                latest_bunjou = latest_bunjou[latest_bunjou["year_int"] == latest_starts_year]
                total_bunjou = latest_bunjou["value"].sum()
                st.metric("分譲着工（合計）", f"{total_bunjou:,.0f} 戸", help=f"{latest_starts_year}年")

        st.markdown("---")

        # ランキング
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("🏆 人口ランキング")
            if not latest_pop.empty:
                rank_pop = latest_pop[["city_name", "value"]].sort_values("value", ascending=False).reset_index(drop=True)
                rank_pop.index = rank_pop.index + 1
                rank_pop.columns = ["市", f"人口（{latest_year}年）"]
                rank_pop[f"人口（{latest_year}年）"] = rank_pop[f"人口（{latest_year}年）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(rank_pop, use_container_width=True)

        with col_right:
            st.subheader("🏗️ 着工戸数ランキング")
            if not latest_starts.empty:
                rank_starts = latest_starts[["city_name", "value"]].sort_values("value", ascending=False).reset_index(drop=True)
                rank_starts.index = rank_starts.index + 1
                rank_starts.columns = ["市", f"着工戸数（{latest_starts_year}年）"]
                rank_starts[f"着工戸数（{latest_starts_year}年）"] = rank_starts[f"着工戸数（{latest_starts_year}年）"].apply(lambda x: f"{x:,.0f}")
                st.dataframe(rank_starts, use_container_width=True)

        # 着工シェア円グラフ
        st.subheader("📊 着工戸数シェア")
        if not latest_starts.empty:
            fig_share = px.pie(
                latest_starts, values="value", names="city_name",
                title=f"着工新設住宅シェア（{latest_starts_year}年）",
                color="city_name", color_discrete_map=CITY_COLORS,
            )
            fig_share.update_traces(textinfo="label+percent+value")
            fig_share.update_layout(height=450)
            st.plotly_chart(fig_share, use_container_width=True)
    else:
        st.info("データを読み込めませんでした。")


# ============================================================
# タブ2: 人口・世帯
# ============================================================
with tab2:
    st.header("👥 人口・世帯トレンド")

    if not df_pop.empty:
        y_min, y_max = year_range_pop

        # 総人口推移
        st.subheader("総人口の推移")
        df_total_pop = filter_df(df_pop, selected_codes, "A1101", y_min, y_max)
        if not df_total_pop.empty:
            fig = make_line_chart(df_total_pop, "総人口の推移", "人口（人）")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_total_pop)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "population_total.csv")

        # 世帯数推移
        st.subheader("世帯数の推移")
        df_households = filter_df(df_pop, selected_codes, "A1500", y_min, y_max)
        if not df_households.empty:
            fig = make_line_chart(df_households, "世帯数の推移", "世帯数")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_households)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "households.csv")

        # 年齢構成比較（最新年）
        st.subheader("年齢構成比較")
        age_codes = {"A1301": "15歳未満", "A1302": "15-64歳", "A1303": "65歳以上"}
        df_age = filter_df_multi(df_pop, selected_codes, list(age_codes.keys()), y_min, y_max)
        if not df_age.empty:
            df_age["year_int"] = df_age["year"].astype(int)
            latest_age_year = df_age["year_int"].max()
            df_age_latest = df_age[df_age["year_int"] == latest_age_year].copy()
            df_age_latest["age_group"] = df_age_latest["indicator_code"].map(age_codes)

            if not df_age_latest.empty:
                fig_age = px.bar(
                    df_age_latest.sort_values("city_name"),
                    x="city_name", y="value", color="age_group",
                    barmode="stack",
                    title=f"年齢構成別人口（{latest_age_year}年）",
                    labels={"city_name": "市", "value": "人口", "age_group": "年齢区分"},
                    color_discrete_sequence=["#2ca02c", "#1f77b4", "#d62728"],
                )
                fig_age.update_layout(height=450)
                st.plotly_chart(fig_age, use_container_width=True)

        # 社会増減
        st.subheader("転入・転出の推移")
        col_in, col_out = st.columns(2)
        with col_in:
            df_in = filter_df(df_pop, selected_codes, "A1700", y_min, y_max)
            if not df_in.empty:
                fig = make_line_chart(df_in, "転入者数", "人数（人）")
                st.plotly_chart(fig, use_container_width=True)
        with col_out:
            df_out = filter_df(df_pop, selected_codes, "A1701", y_min, y_max)
            if not df_out.empty:
                fig = make_line_chart(df_out, "転出者数", "人数（人）")
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("人口データが読み込めませんでした。")


# ============================================================
# タブ3: 住宅着工統計
# ============================================================
with tab3:
    st.header("🏗️ 住宅着工統計")

    if not df_housing.empty:
        y_min, y_max = year_range_housing

        # 着工戸数（合計）推移
        st.subheader("着工新設住宅 合計の推移")
        df_starts_total = filter_df(df_housing, selected_codes, "H1800", y_min, y_max)
        if not df_starts_total.empty:
            fig = make_bar_chart(df_starts_total, "着工新設住宅（合計）", "戸数")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_starts_total)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "housing_starts_total.csv")

        # 利用関係別（特定市の詳細）
        st.subheader("利用関係別の内訳推移")

        detail_city = st.selectbox(
            "詳細を表示する市を選択",
            selected_cities,
            key="detail_city_starts"
        )
        detail_code = CITY_NAMES.get(detail_city, "")

        if detail_code:
            type_codes = {"H1801": "持家", "H1802": "貸家", "H1803": "分譲"}
            df_by_type = filter_df_multi(
                df_housing, [detail_code], list(type_codes.keys()), y_min, y_max
            )
            if not df_by_type.empty:
                df_by_type["type"] = df_by_type["indicator_code"].map(type_codes)
                fig_type = px.bar(
                    df_by_type.sort_values("year"),
                    x="year", y="value", color="type",
                    barmode="stack",
                    title=f"{detail_city}：利用関係別 着工戸数の推移",
                    labels={"year": "年", "value": "戸数", "type": "利用関係"},
                    color_discrete_map={"持家": "#1f77b4", "貸家": "#ff7f0e", "分譲": "#2ca02c"},
                )
                fig_type.update_layout(height=450)
                st.plotly_chart(fig_type, use_container_width=True)

                # ピボットテーブル
                pivot_type = df_by_type.pivot_table(
                    values="value", index="year", columns="type", aggfunc="first"
                ).sort_index(ascending=False)
                st.dataframe(pivot_type.style.format("{:,.0f}"), use_container_width=True)
                download_button(pivot_type, f"housing_starts_{detail_city}.csv")

        # 貸家着工の市間比較
        st.subheader("🏢 貸家着工の市間比較")
        df_kashiya = filter_df(df_housing, selected_codes, "H1802", y_min, y_max)
        if not df_kashiya.empty:
            fig = make_line_chart(df_kashiya, "貸家着工戸数の推移", "戸数")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_kashiya)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "housing_starts_kashiya.csv")

        # 分譲着工の市間比較
        st.subheader("🏡 分譲着工の市間比較")
        df_bunjou = filter_df(df_housing, selected_codes, "H1803", y_min, y_max)
        if not df_bunjou.empty:
            fig = make_line_chart(df_bunjou, "分譲着工戸数の推移", "戸数")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_bunjou)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "housing_starts_bunjou.csv")

        # 床面積の推移
        st.subheader("📐 着工床面積の推移")
        df_floor = filter_df(df_housing, selected_codes, "H2600", y_min, y_max)
        if not df_floor.empty:
            fig = make_line_chart(df_floor, "着工新設住宅 床面積の推移", "床面積（㎡）")
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("住宅着工データが読み込めませんでした。")


# ============================================================
# タブ4: 住宅ストック
# ============================================================
with tab4:
    st.header("🏘️ 住宅ストック・リフォーム市場")

    if not df_housing.empty:
        # 総住宅数
        st.subheader("総住宅数の推移")
        df_stock = filter_df(df_housing, selected_codes, "H1100", 1980, 2025)
        if not df_stock.empty:
            fig = make_bar_chart(df_stock, "総住宅数の推移", "住宅数（戸）")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_stock)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "housing_stock.csv")

        # 空き家数
        st.subheader("空き家数の推移")
        df_vacant = filter_df(df_housing, selected_codes, "H110202", 1980, 2025)
        if not df_vacant.empty:
            fig = make_bar_chart(df_vacant, "空き家数の推移", "空き家数（戸）")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_vacant)
            st.dataframe(pivot.style.format("{:,.0f}"), use_container_width=True)
            download_button(pivot, "vacant_houses.csv")

        # 木造・非木造比較
        st.subheader("🪵 木造 vs 非木造住宅")
        detail_city2 = st.selectbox(
            "詳細を表示する市を選択",
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
                fig_struct.update_layout(height=450)
                st.plotly_chart(fig_struct, use_container_width=True)

        # 築年数別ストック
        st.subheader("🏚️ 築年数別住宅ストック")
        detail_city3 = st.selectbox(
            "詳細を表示する市を選択",
            selected_cities,
            key="detail_city_age"
        )
        detail_code3 = CITY_NAMES.get(detail_city3, "")

        if detail_code3:
            age_codes_map = {
                "H1615": "～1960年",
                "H1612": "1971～1980年",
                "H1613": "1981～1990年",
                "H1619": "1991～2000年",
                "H1620": "2001～2005年",
                "H1622": "2006～2010年",
                "H1624": "2011～2015年",
                "H1626": "2016～2020年",
                "H1627": "2021～2023年",
            }
            df_build_age = filter_df_multi(
                df_housing, [detail_code3], list(age_codes_map.keys()), 1980, 2025
            )
            if not df_build_age.empty:
                # 最新年のデータのみ
                df_build_age["year_int"] = df_build_age["year"].astype(int)
                latest = df_build_age["year_int"].max()
                df_build_latest = df_build_age[df_build_age["year_int"] == latest].copy()
                df_build_latest["period"] = df_build_latest["indicator_code"].map(age_codes_map)

                if not df_build_latest.empty:
                    # 並び順を設定
                    period_order = list(age_codes_map.values())
                    df_build_latest["period"] = pd.Categorical(
                        df_build_latest["period"], categories=period_order, ordered=True
                    )
                    df_build_latest = df_build_latest.sort_values("period")

                    fig_age = px.bar(
                        df_build_latest,
                        x="period", y="value",
                        title=f"{detail_city3}：築年数別住宅数（{latest}年時点）",
                        labels={"period": "建築時期", "value": "住宅数（戸）"},
                        color_discrete_sequence=["#e377c2"],
                    )
                    fig_age.update_layout(height=450)
                    st.plotly_chart(fig_age, use_container_width=True)

                    st.caption("💡 築20年以上（2005年以前建築）のストックがリフォーム需要の潜在市場です。")
    else:
        st.info("住宅ストックデータが読み込めませんでした。")


# ============================================================
# タブ5: 指標比較
# ============================================================
with tab5:
    st.header("📊 社会生活統計指標の比較")

    if not df_indicators.empty:
        # 持ち家比率
        st.subheader("持ち家比率の推移")
        df_own = filter_df(df_indicators, selected_codes, "H3110", 1980, 2025)
        if not df_own.empty:
            fig = make_line_chart(df_own, "持ち家比率の推移", "比率（%）")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_own)
            st.dataframe(pivot.style.format("{:.1f}"), use_container_width=True)
            download_button(pivot, "home_ownership_rate.csv")

        # 空き家比率
        st.subheader("空き家比率の推移")
        df_vacancy = filter_df(df_indicators, selected_codes, "H3410", 1980, 2025)
        if not df_vacancy.empty:
            fig = make_line_chart(df_vacancy, "空き家比率の推移", "比率（%）")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_vacancy)
            st.dataframe(pivot.style.format("{:.1f}"), use_container_width=True)
            download_button(pivot, "vacancy_rate.csv")

        # 1住宅当たり延べ面積
        st.subheader("1住宅当たり延べ面積")
        df_area = filter_df(df_indicators, selected_codes, "H6110", 1980, 2025)
        if not df_area.empty:
            fig = make_line_chart(df_area, "1住宅当たり延べ面積の推移", "面積（㎡）")
            st.plotly_chart(fig, use_container_width=True)

        # 1000世帯当たり着工戸数
        st.subheader("1000世帯当たり新設住宅着工戸数")
        df_per1000 = filter_df(df_indicators, selected_codes, "H7100", 2000, 2025)
        if not df_per1000.empty:
            fig = make_line_chart(df_per1000, "1000世帯当たり着工戸数の推移", "戸数/1000世帯")
            st.plotly_chart(fig, use_container_width=True)

            pivot = make_pivot_table(df_per1000)
            st.dataframe(pivot.style.format("{:.1f}"), use_container_width=True)
            download_button(pivot, "starts_per_1000households.csv")
    else:
        st.info("指標データが読み込めませんでした。")


# ============================================================
# フッター
# ============================================================

st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #888; font-size: 0.85em;">
        📊 商圏エリアデータダッシュボード v1.0（フェーズ1）<br>
        データ出典: <a href="https://www.e-stat.go.jp/" target="_blank">e-Stat（政府統計の総合窓口）</a>
        ・社会・人口統計体系 市区町村データ<br>
        最終データ更新: CSVファイルのタイムスタンプを確認
    </div>
    """,
    unsafe_allow_html=True,
)
