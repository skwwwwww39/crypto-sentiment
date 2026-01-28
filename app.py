import streamlit as st
import requests

st.set_page_config(page_title="Connection Test", layout="wide")

st.title("🛠 API Connection Diagnostics")

# あなたのAPIキー
CRYPTOPANIC_API_KEY = "ce5d1a3effe7a877dcf19adbce33ef35ded05f5e"

if st.button("テスト接続を実行 (Test Connection)"):
    # 1. Risingフィルタなしで、純粋に最新投稿を取りに行く
    url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&public=true"
    
    # ヘッダー（ブラウザのふりをする）
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        st.write("接続試行中... (Connecting...)")
        response = requests.get(url, headers=headers, timeout=10)
        
        # 結果を表示
        st.subheader("診断結果")
        st.write(f"**Status Code:** {response.status_code}")
        
        if response.status_code == 200:
            st.success("✅ 接続成功！データは正常に取得できています。")
            data = response.json()
            count = len(data.get("results", []))
            st.write(f"取得できたデータ数: {count}件")
            st.json(data) # データの生中身を表示
        elif response.status_code == 401:
            st.error("❌ 401 Unauthorized: APIキーが間違っています。")
        elif response.status_code == 403:
            st.error("❌ 403 Forbidden: アクセスが拒否されました。WAF/Cloudflareにブロックされています。")
            st.text(response.text) # エラー画面の中身を表示
        elif response.status_code == 429:
            st.error("❌ 429 Too Many Requests: リクエストの送りすぎです。しばらく待ってください。")
        else:
            st.error(f"❌ エラー発生: {response.status_code}")
            st.text(response.text) # 生のエラー内容

    except Exception as e:
        st.error(f"通信エラー: {e}")