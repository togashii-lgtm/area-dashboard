# 商圏エリアデータダッシュボード（愛知県11市）

愛知県内の西三河（8市）および知多（3市）を対象とした、住宅・不動産マーケティング用の市場データ収集・分析ダッシュボードです。

## 対象自治体（11市）
- **西三河エリア**: 岡崎市、碧南市、刈谷市、豊田市、安城市、西尾市、知立市、高浜市
- **知多エリア**: 東海市、大府市、知多市

## 取得・可視化データ（フェーズ1）
- **人口・世帯動向**: 総人口推移、世帯数推移、年齢構成（年少・生産年齢・老年）、転入・転出数
- **住宅着工統計**: 新設住宅着工戸数（合計、持家、貸家、分譲）、着工床面積推移
- **住宅ストック・リフォーム指標**: 持ち家比率、空き家比率、木造/非木造比率、築年数別住宅数推移

## 技術構成
- **フロントエンド / UI**: Streamlit, Plotly
- **データ取得・加工**: Python, e-Stat API（社会・人口統計体系）
- **自動更新**: GitHub Actions（毎月5日定期実行）
- **ホスティング**: Streamlit Community Cloud

## セットアップ手順

### ローカル起動
```bash
pip install -r requirements.txt
python scripts/fetch_data.py  # 初回データ取得
streamlit run app.py
```

### Streamlit Community Cloud でのSecrets設定
アプリのデプロイ後、Streamlit Cloudの「Settings」>「Secrets」に以下を設定してください。

```toml
password = "社内共通の閲覧パスワード"
```

### GitHub Actions の Secrets 設定
リポジトリの「Settings」>「Secrets and variables」>「Actions」に以下を追加してください。
- `ESTAT_API_KEY`: e-StatのアプリケーションID
