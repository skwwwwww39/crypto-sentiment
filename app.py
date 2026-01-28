import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
from datetime import datetime

# --- 1. 設定と準備 ---
st.set_page_config(page_title="Crypto AI Dashboard", layout="wide")

# デザイン（CSS）
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .metric-card {
        background-color: #1E1E1E;
        border: 1px solid #333;
        padding: 20px;
        border-radius: 10px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Google AI (Gemini) の設定 ---
# 本番環境(Streamlit Cloud)とローカル環境でキーの読み込み方を変える
try:
    # Streamlit CloudのSecretsから読み込み
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    # ローカル環境(.envなど)または入力がない場合
    api_key = os.getenv("GEMINI_API_KEY")

# サイドバーでキー入力もできるようにする（テスト用）
with st.sidebar:
    st.header("⚙️ Settings")
    if not api_key:
        api_key = st.text_input("Enter Google API Key", type="password")
    
    st.info("API Keyがあれば、AIが感情分析を行います。")

# AIモデルの準備
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-pro')

# --- 3. 関数（AI分析ロジック） ---
def analyze_sentiment(text):
    """Geminiを使ってテキストの感情を分析する"""
    if not api_key:
        return "Unknown", 0  # キーがない場合は何もしない

    prompt = f"""
    あなたは暗号資産のトレーダー心理を分析するプロです。
    以下の投稿文を分析し、次の6つの感情のどれかに分類してください:
    [Despair, Fear, Negative, Positive, Optimism, Euphoria]
    
    また、その感情の強さを -100 (Despair) から 100 (Euphoria) のスコアで評価してください。
    
    出力形式:
    Label: [ここにラベル]
    Score: [ここに数値]
    
    投稿文: "{text}"
    """
    
    try:
        response = model.generate_content(prompt)
        content = response.text
        
        # AIの返事からラベルとスコアを抜き出す簡易処理
        label = "Neutral"
        score = 0
        
        for line in content.split('\n'):
            if "Label:" in line:
                label = line.split(":")[-1].strip()
            if "Score:" in line:
                try:
                    score = int(line.split(":")[-1].strip())
                except:
                    pass
        return label, score
    except Exception as e:
        return "Error", 0

# --- 4. メイン画面のUI ---
st.title("🔮 Crypto Sentiment AI")
st.markdown("市場の声をAIが分析し、感情を可視化します。")

# データ入力エリア
col1, col2 = st.columns([2, 1])

with col1:
    user_input = st.text_area("分析したい投稿を入力 (例: Bitcoin is crashing! It's over!)", height=100)
    analyze_btn = st.button("AI分析実行 🚀", type="primary")

# 分析結果の表示
if analyze_btn and user_input:
    with st.spinner("AIが分析中..."):
        label, score = analyze_sentiment(user_input)
    
    st.divider()
    
    # 結果カード表示
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"<div class='metric-card'><h3>Emotion</h3><h2>{label}</h2></div>", unsafe_allow_html=True)
    with c2:
        st.markdown(f"<div class='metric-card'><h3>Score</h3><h2>{score}</h2></div>", unsafe_allow_html=True)
    with c3:
        color = "red" if score < 0 else "green"
        st.markdown(f"<div class='metric-card' style='border-color:{color};'><h3>Signal</h3><h2 style='color:{color};'>{'BEAR' if score < 0 else 'BULL'}</h2></div>", unsafe_allow_html=True)

    # ゲージチャート
    fig = px.bar(x=[score], y=["Sentiment"], orientation='h', range_x=[-100, 100], 
                 color=[score], color_continuous_scale='RdYlGn')
    fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
    st.plotly_chart(fig, use_container_width=True)

# 履歴テーブル（デモ用）
st.subheader("📝 Recent Logs")
demo_data = {
    "Time": [datetime.now().strftime("%H:%M")],
    "Text": [user_input if user_input else "No input yet"],
    "Emotion": [label if analyze_btn else "-"]
}
st.table(pd.DataFrame(demo_data))