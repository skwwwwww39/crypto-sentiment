import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
from datetime import datetime

# --- 1. 設定と準備 ---
st.set_page_config(page_title="Crypto AI Dashboard", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .metric-card {
        background-color: #1E1E1E; border: 1px solid #333;
        padding: 20px; border-radius: 10px; text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. 変数の初期化（NameError防止の安全策） ---
# ここで最初に変数を宣言しておくことで、エラーで止まるのを防ぎます
label = "Waiting..."
score = 0
analyze_executed = False 
error_msg = ""

# --- 3. Google AI (Gemini) の設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

# ★ここをあなたの画面に合わせて変更しました
if api_key:
    genai.configure(api_key=api_key)
    # 404エラー対策: 画像にある 'gemini-flash-latest' を使用
    model = genai.GenerativeModel('gemini-flash-latest')

# --- 4. 関数（AI分析ロジック） ---
def analyze_sentiment(text):
    if not api_key:
        return "No API Key", 0, "APIキーが設定されていません。Secretsを確認してください。"

    # AIへの指示（プロンプト）
    prompt = f"""
    Analyze the sentiment of this crypto market post: "{text}"
    Classify into exactly one: [Despair, Fear, Negative, Positive, Optimism, Euphoria]
    Score from -100 to 100.
    Output format:
    Label: [Label]
    Score: [Number]
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text
        
        # 解析処理
        res_label = "Neutral"
        res_score = 0
        for line in content.split('\n'):
            if "Label:" in line:
                res_label = line.split(":")[-1].strip()
            if "Score:" in line:
                try:
                    res_score = int(line.split(":")[-1].strip())
                except:
                    pass
        return res_label, res_score, None # エラーなし
    except Exception as e:
        return "Error", 0, str(e) # エラー内容を返す

# --- 5. メイン画面のUI ---
st.title("🔮 Crypto Sentiment AI")

# データ入力エリア
col1, col2 = st.columns([2, 1])
with col1:
    user_input = st.text_area("分析したい投稿を入力 (例: Bitcoin is crashing! It's over!)", height=100)
    analyze_btn = st.button("AI分析実行 🚀", type="primary")

# 分析実行ボタンが押されたとき
if analyze_btn and user_input:
    with st.spinner("AIが分析中..."):
        # 関数を呼び出して結果を上書き
        label, score, error_msg = analyze_sentiment(user_input)
        analyze_executed = True
        
        # エラー判定
        if label == "Error":
            st.error(f"AIエラー: {error_msg}")
        elif label == "No API Key":
            st.warning("Streamlit CloudのSettings > SecretsにAPIキーを設定してください。")

# 結果表示 (分析済み、かつエラーでない場合のみ表示)
if analyze_executed and label != "Error" and label != "No API Key":
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><h3>Emotion</h3><h2>{label}</h2></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><h3>Score</h3><h2>{score}</h2></div>", unsafe_allow_html=True)
    with c3:
        color = "red" if score < 0 else "green"
        signal_text = "BEAR" if score < 0 else "BULL"
        st.markdown(f"<div class='metric-card' style='border-color:{color};'><h3>Signal</h3><h2 style='color:{color};'>{signal_text}</h2></div>", unsafe_allow_html=True)

    # グラフ
    fig = px.bar(x=[score], y=["Sentiment"], orientation='h', range_x=[-100, 100], 
                 color=[score], color_continuous_scale='RdYlGn')
    
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
    st.plotly_chart(fig, use_container_width=True) 

# 履歴テーブル（ここでのNameErrorも修正済み）
st.subheader("📝 Recent Logs")
demo_data = {
    "Time": [datetime.now().strftime("%H:%M")],
    "Text": [user_input if user_input else "-"],
    "Emotion": [label]
}
st.table(pd.DataFrame(demo_data))