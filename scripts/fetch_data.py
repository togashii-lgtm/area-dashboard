"""
e-Stat API からデータを取得し、CSV形式で保存するスクリプト
対象: 愛知県内11市（西三河8市 + 知多3市）
"""

import urllib.request
import urllib.parse
import json
import ssl
import csv
import os
import sys
import time
from collections import defaultdict

# ============================================================
# 設定
# ============================================================

# APIキー（環境変数 or 直接指定）
APP_ID = os.environ.get("ESTAT_API_KEY", "c9272f14764d5d8de4a1241c77d862a180209d4b")

# SSL設定
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 対象11市
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

# 出力先
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

# ============================================================
# API ヘルパー
# ============================================================

def api_get(endpoint, params, max_retries=3):
    """e-Stat API を呼び出し、JSONレスポンスを返す"""
    base = f"https://api.e-stat.go.jp/rest/3.0/app/json/{endpoint}"
    params["appId"] = APP_ID
    qs = urllib.parse.urlencode(params, encoding="utf-8")
    url = f"{base}?{qs}"

    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ssl_context, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt < max_retries - 1:
                wait = (attempt + 1) * 5
                print(f"  リトライ {attempt + 1}/{max_retries} ({wait}秒後): {e}")
                time.sleep(wait)
            else:
                raise


def fetch_all_data(stats_data_id, cd_area, cd_cat01=None, limit=100000):
    """ページネーション対応のデータ一括取得"""
    all_values = []
    class_info = None
    next_key = None

    while True:
        params = {
            "statsDataId": stats_data_id,
            "cdArea": cd_area,
            "metaGetFlg": "Y",
            "cntGetFlg": "N",
            "limit": str(limit),
        }
        if cd_cat01:
            params["cdCat01"] = cd_cat01
        if next_key:
            params["startPosition"] = str(next_key)

        data = api_get("getStatsData", params)
        result = data.get("GET_STATS_DATA", {}).get("RESULT", {})

        if result.get("STATUS") != 0:
            print(f"  エラー: {result.get('ERROR_MSG', 'Unknown')}")
            break

        stat_data = data.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})

        # メタ情報（初回のみ）
        if class_info is None:
            class_info = {}
            class_objs = stat_data.get("CLASS_INF", {}).get("CLASS_OBJ", [])
            if isinstance(class_objs, dict):
                class_objs = [class_objs]
            for ci in class_objs:
                axis_id = ci.get("@id", "")
                classes = ci.get("CLASS", [])
                if isinstance(classes, dict):
                    classes = [classes]
                class_info[axis_id] = {c["@code"]: c.get("@name", "") for c in classes}

        # データ値
        values = stat_data.get("DATA_INF", {}).get("VALUE", [])
        if isinstance(values, dict):
            values = [values]
        all_values.extend(values)

        # ページネーション
        next_key_val = stat_data.get("DATA_INF", {}).get("NEXT_KEY")
        if next_key_val:
            next_key = int(next_key_val)
            print(f"  ページネーション: {len(all_values)}件取得済、次={next_key}")
        else:
            break

    return all_values, class_info


# ============================================================
# データ取得・保存関数
# ============================================================

def fetch_population():
    """人口・世帯データを取得"""
    print("=" * 60)
    print("人口・世帯データを取得中...")
    print("=" * 60)

    # 取得する項目
    target_cats = {
        "A1101": "総人口",
        "A110101": "総人口_男",
        "A110102": "総人口_女",
        "A1102": "日本人人口",
        "A1200": "人口密度",
        "A1301": "15歳未満人口",
        "A1302": "15-64歳人口",
        "A1303": "65歳以上人口",
        "A130301": "75歳以上人口",
        "A1500": "世帯数",
        "A1700": "転入者数",
        "A1701": "転出者数",
        "A1702": "社会増減数",
        "A4101": "出生数",
        "A4200": "死亡数",
    }

    cd_area = ",".join(CITIES.keys())
    cd_cat01 = ",".join(target_cats.keys())

    values, class_info = fetch_all_data("0000020201", cd_area, cd_cat01)
    print(f"  取得件数: {len(values)}")

    # CSV整形
    rows = []
    for v in values:
        area_code = v.get("@area", "")
        cat_code = v.get("@cat01", "")
        time_code = v.get("@time", "")
        value = v.get("$", "")
        unit = v.get("@unit", "")

        if area_code not in CITIES:
            continue

        year = time_code[:4] if time_code else ""
        city = CITIES[area_code]
        cat_name = target_cats.get(cat_code, class_info.get("cat01", {}).get(cat_code, cat_code))

        rows.append({
            "city_code": area_code,
            "city_name": city["name"],
            "area_group": city["area"],
            "year": year,
            "indicator_code": cat_code,
            "indicator_name": cat_name,
            "value": value,
            "unit": unit,
        })

    # 保存
    output_path = os.path.join(DATA_DIR, "population.csv")
    fieldnames = ["city_code", "city_name", "area_group", "year", "indicator_code", "indicator_name", "value", "unit"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["city_code"], r["indicator_code"], r["year"])))

    print(f"  保存完了: {output_path} ({len(rows)}行)")
    return len(rows)


def fetch_housing_starts():
    """住宅着工統計・住宅ストックデータを取得"""
    print("=" * 60)
    print("住宅着工・ストックデータを取得中...")
    print("=" * 60)

    target_cats = {
        # 着工新設住宅（戸数）
        "H1800": "着工新設住宅_合計",
        "H1801": "着工新設住宅_持家",
        "H1802": "着工新設住宅_貸家",
        "H1803": "着工新設住宅_分譲",
        "H1804": "着工新設住宅_給与",
        "H1810": "着工新設住宅_持家分譲計",
        # 着工新設住宅（床面積）
        "H2500": "着工居住用建築物_床面積",
        "H2600": "着工新設住宅_床面積_合計",
        "H2601": "着工新設住宅_床面積_持家",
        "H2602": "着工新設住宅_床面積_分譲",
        "H2603": "着工新設住宅_床面積_貸家",
        "H2604": "着工新設住宅_床面積_給与",
        # 住宅ストック
        "H1100": "総住宅数",
        "H1101": "居住世帯あり住宅数",
        "H1102": "居住世帯なし住宅数",
        "H110202": "空き家数",
        "H1310": "持ち家数",
        # 木造・非木造
        "H1501": "木造住宅数",
        "H1502": "非木造住宅数",
        "H140101": "一戸建_木造",
        "H140102": "一戸建_非木造",
        "H140301": "共同住宅_木造",
        "H140302": "共同住宅_非木造",
        # 築年数別
        "H1615": "1960年以前建築住宅数",
        "H1616": "1970年以前建築住宅数",
        "H1612": "1971-1980年建築住宅数",
        "H1613": "1981-1990年建築住宅数",
        "H1619": "1991-2000年建築住宅数",
        "H1620": "2001-2005年建築住宅数",
        "H1622": "2006-2010年建築住宅数",
        "H1624": "2011-2015年建築住宅数",
        "H1626": "2016-2020年建築住宅数",
        "H1627": "2021-2023年9月建築住宅数",
        # リフォーム関連
        "H2270": "耐震工事をした住宅数_持ち家",
    }

    cd_area = ",".join(CITIES.keys())
    cd_cat01 = ",".join(target_cats.keys())

    values, class_info = fetch_all_data("0000020208", cd_area, cd_cat01)
    print(f"  取得件数: {len(values)}")

    # CSV整形
    rows = []
    for v in values:
        area_code = v.get("@area", "")
        cat_code = v.get("@cat01", "")
        time_code = v.get("@time", "")
        value = v.get("$", "")
        unit = v.get("@unit", "")

        if area_code not in CITIES:
            continue

        year = time_code[:4] if time_code else ""
        city = CITIES[area_code]
        cat_name = target_cats.get(cat_code, class_info.get("cat01", {}).get(cat_code, cat_code))

        rows.append({
            "city_code": area_code,
            "city_name": city["name"],
            "area_group": city["area"],
            "year": year,
            "indicator_code": cat_code,
            "indicator_name": cat_name,
            "value": value,
            "unit": unit,
        })

    # 保存
    output_path = os.path.join(DATA_DIR, "housing.csv")
    fieldnames = ["city_code", "city_name", "area_group", "year", "indicator_code", "indicator_name", "value", "unit"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["city_code"], r["indicator_code"], r["year"])))

    print(f"  保存完了: {output_path} ({len(rows)}行)")
    return len(rows)


def fetch_housing_indicators():
    """住宅関連の社会生活統計指標を取得"""
    print("=" * 60)
    print("住宅指標データを取得中...")
    print("=" * 60)

    target_cats = {
        "H3110": "持ち家比率",
        "H3120": "借家比率",
        "H3410": "空き家比率",
        "H6110": "1住宅当たり延べ面積",
        "H6114": "1住宅当たり延べ面積_持ち家",
        "H6116": "1住宅当たり延べ面積_借家",
        "H7100": "新設住宅着工戸数_1000世帯当たり",
    }

    cd_area = ",".join(CITIES.keys())
    cd_cat01 = ",".join(target_cats.keys())

    values, class_info = fetch_all_data("0000020308", cd_area, cd_cat01)
    print(f"  取得件数: {len(values)}")

    rows = []
    for v in values:
        area_code = v.get("@area", "")
        cat_code = v.get("@cat01", "")
        time_code = v.get("@time", "")
        value = v.get("$", "")
        unit = v.get("@unit", "")

        if area_code not in CITIES:
            continue

        year = time_code[:4] if time_code else ""
        city = CITIES[area_code]
        cat_name = target_cats.get(cat_code, class_info.get("cat01", {}).get(cat_code, cat_code))

        rows.append({
            "city_code": area_code,
            "city_name": city["name"],
            "area_group": city["area"],
            "year": year,
            "indicator_code": cat_code,
            "indicator_name": cat_name,
            "value": value,
            "unit": unit,
        })

    output_path = os.path.join(DATA_DIR, "housing_indicators.csv")
    fieldnames = ["city_code", "city_name", "area_group", "year", "indicator_code", "indicator_name", "value", "unit"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["city_code"], r["indicator_code"], r["year"])))

    print(f"  保存完了: {output_path} ({len(rows)}行)")
    return len(rows)


# ============================================================
# メイン
# ============================================================

if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)

    print(f"データ出力先: {DATA_DIR}")
    print(f"対象市数: {len(CITIES)}")
    print()

    total = 0
    total += fetch_population()
    print()
    total += fetch_housing_starts()
    print()
    total += fetch_housing_indicators()

    print()
    print("=" * 60)
    print(f"全データ取得完了！ 合計 {total} 行")
    print("=" * 60)
