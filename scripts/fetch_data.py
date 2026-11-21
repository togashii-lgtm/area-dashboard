"""
e-Stat API からデータを取得し、CSV形式で保存するスクリプト（拡張版）
- 世帯構成（単独世帯・核家族世帯・その他）
- 住宅所有関係（持ち家世帯・借家世帯）
- 人口純移動（転入超過数）
- 移動元・移動先（ODデータ：転入元TOP / 転出先TOP）
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

APP_ID = os.environ.get("ESTAT_API_KEY", "c9272f14764d5d8de4a1241c77d862a180209d4b")

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

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

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def api_get(endpoint, params, max_retries=3):
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
                wait = (attempt + 1) * 3
                time.sleep(wait)
            else:
                raise


def fetch_all_data(stats_data_id, cd_area, cd_cat01=None, limit=100000):
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
            break

        stat_data = data.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})

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

        values = stat_data.get("DATA_INF", {}).get("VALUE", [])
        if isinstance(values, dict):
            values = [values]
        all_values.extend(values)

        next_key_val = stat_data.get("DATA_INF", {}).get("NEXT_KEY")
        if next_key_val:
            next_key = int(next_key_val)
        else:
            break

    return all_values, class_info


def fetch_population_extended():
    print("人口・世帯（単身・家族構成含む）データを取得中...")

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
        "A710101": "一般世帯数",
        # 世帯構造（単身・家族）
        "A810105": "単独世帯数_一人暮らし",
        "A810102": "核家族世帯数_家族",
        "A810103": "核家族以外の世帯数_三世代等",
        "A810101": "親族のみの世帯数",
        # 移動
        "A1700": "転入者数",
        "A1701": "転出者数",
        "A1702": "社会増減数_転入超過数",
        "A4101": "出生数",
        "A4200": "死亡数",
    }

    cd_area = ",".join(CITIES.keys())
    cd_cat01 = ",".join(target_cats.keys())

    values, class_info = fetch_all_data("0000020201", cd_area, cd_cat01)

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

    output_path = os.path.join(DATA_DIR, "population.csv")
    fieldnames = ["city_code", "city_name", "area_group", "year", "indicator_code", "indicator_name", "value", "unit"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["city_code"], r["indicator_code"], r["year"])))

    print(f"  -> population.csv: {len(rows)}行 保存完了")


def fetch_housing_extended():
    print("住宅着工・ストック（持ち家/借家含む）データを取得中...")

    target_cats = {
        # 着工戸数
        "H1800": "着工新設住宅_合計",
        "H1801": "着工新設住宅_持家",
        "H1802": "着工新設住宅_貸家",
        "H1803": "着工新設住宅_分譲",
        "H1804": "着工新設住宅_給与",
        "H1810": "着工新設住宅_持家分譲計",
        # 床面積
        "H2500": "着工居住用建築物_床面積",
        "H2600": "着工新設住宅_床面積_合計",
        "H2601": "着工新設住宅_床面積_持家",
        "H2602": "着工新設住宅_床面積_分譲",
        "H2603": "着工新設住宅_床面積_貸家",
        # 現住居の所有関係（持ち家世帯 vs 借家世帯）
        "H1310": "持ち家世帯数_現住居持ち家",
        "H1320": "借家世帯数_現住居賃貸",
        "H1322": "民営借家世帯数_民間アパート等",
        "H1321": "公営公社借家世帯数",
        # ストック
        "H1100": "総住宅数",
        "H1101": "居住世帯あり住宅数",
        "H1102": "居住世帯なし住宅数",
        "H110202": "空き家数",
        # 木造
        "H1501": "木造住宅数",
        "H1502": "非木造住宅数",
        "H140101": "一戸建_木造",
        "H140102": "一戸建_非木造",
        "H140301": "共同住宅_木造",
        "H140302": "共同住宅_非木造",
        # 築年数
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
        "H2270": "耐震工事をした住宅数_持ち家",
    }

    cd_area = ",".join(CITIES.keys())
    cd_cat01 = ",".join(target_cats.keys())

    values, class_info = fetch_all_data("0000020208", cd_area, cd_cat01)

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

    output_path = os.path.join(DATA_DIR, "housing.csv")
    fieldnames = ["city_code", "city_name", "area_group", "year", "indicator_code", "indicator_name", "value", "unit"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda r: (r["city_code"], r["indicator_code"], r["year"])))

    print(f"  -> housing.csv: {len(rows)}行 保存完了")


def fetch_migration_od():
    """11市の転入元TOP・転出先TOPデータを取得（住民基本台帳人口移動報告：2022年）"""
    print("転入元・転出先（ODデータ）を取得中...")

    rows = []
    for city_code, city_meta in CITIES.items():
        city_name = city_meta["name"]
        print(f"  {city_name} ({city_code}) の移動データを照会...")
        
        # 1. 転出先（この市からどこへ引っ越したか）
        try:
            params_out = {
                "statsDataId": "0004003460",
                "cdArea": city_code,
                "cdCat02": "000",
                "cdCat03": "0",
                "metaGetFlg": "Y",
                "cntGetFlg": "N",
                "limit": "10000",
            }
            res = api_get("getStatsData", params_out)
            stat = res.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})
            class_objs = stat.get("CLASS_INF", {}).get("CLASS_OBJ", [])
            dest_names = {}
            for co in class_objs:
                if co.get("@id") == "cat01":
                    for c in co.get("CLASS", []):
                        dest_names[c["@code"]] = c.get("@name", "")

            vals = stat.get("DATA_INF", {}).get("VALUE", [])
            if isinstance(vals, dict): vals = [vals]
            for v in vals:
                dest_code = v.get("@cat01", "")
                dest_name = dest_names.get(dest_code, dest_code)
                val_num = v.get("$", "0")
                if val_num and val_num != "0" and val_num != "-":
                    if dest_code not in ["00000", "01000", city_code]:
                        rows.append({
                            "city_code": city_code,
                            "city_name": city_name,
                            "flow_type": "転出先（流出先）",
                            "partner_code": dest_code,
                            "partner_name": dest_name,
                            "persons": int(val_num),
                            "year": "2022"
                        })
        except Exception as e:
            print(f"    エラー(転出先): {e}")

        # 2. 転入元（どこからこの市へ引っ越してきたか）
        try:
            params_in = {
                "statsDataId": "0004003460",
                "cdCat01": city_code,
                "cdCat02": "000",
                "cdCat03": "0",
                "metaGetFlg": "Y",
                "cntGetFlg": "N",
                "limit": "10000",
            }
            res_in = api_get("getStatsData", params_in)
            stat_in = res_in.get("GET_STATS_DATA", {}).get("STATISTICAL_DATA", {})
            class_objs_in = stat_in.get("CLASS_INF", {}).get("CLASS_OBJ", [])
            origin_names = {}
            for co in class_objs_in:
                if co.get("@id") == "area":
                    for c in co.get("CLASS", []):
                        origin_names[c["@code"]] = c.get("@name", "")

            vals_in = stat_in.get("DATA_INF", {}).get("VALUE", [])
            if isinstance(vals_in, dict): vals_in = [vals_in]
            for v in vals_in:
                orig_code = v.get("@area", "")
                orig_name = origin_names.get(orig_code, orig_code)
                val_num = v.get("$", "0")
                if val_num and val_num != "0" and val_num != "-":
                    if orig_code not in ["00000", "00005", "01000", city_code]:
                        rows.append({
                            "city_code": city_code,
                            "city_name": city_name,
                            "flow_type": "転入元（流入元）",
                            "partner_code": orig_code,
                            "partner_name": orig_name,
                            "persons": int(val_num),
                            "year": "2022"
                        })
        except Exception as e:
            print(f"    エラー(転入元): {e}")

    output_path = os.path.join(DATA_DIR, "migration_od.csv")
    fieldnames = ["city_code", "city_name", "flow_type", "partner_code", "partner_name", "persons", "year"]
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"  -> migration_od.csv: {len(rows)}行 保存完了")


if __name__ == "__main__":
    os.makedirs(DATA_DIR, exist_ok=True)
    fetch_population_extended()
    fetch_housing_extended()
    fetch_migration_od()
    print("全データ取得＆更新完了！")
