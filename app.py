import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
import time
import random
from datetime import datetime

# --- 1. アプリ設定 ---
st.set_page_config(page_title="Crypto AI Dashboard", layout="wide")

# デザイン調整
st.markdown("""
<style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .metric-card {
        background-color: #1E1E1E; border: 1px solid #333;
        padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 10px;
    }
    .sentiment-high { color: #00FF99; }
    .sentiment-low { color: #FF006E; }
</style>
""", unsafe_allow_html=True)

# --- 2. Google AI (Gemini) 設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    # 最新モデルを指定
    model = genai.GenerativeModel('gemini-flash-latest')

# --- 3. 分析ロジック ---
def analyze_text(text):
    """AIを使ってテキストを分析する"""
    if not api_key:
        return "Neutral", 0
    
    # 簡易化のためプロンプトを短くしています
    prompt = f"""
    Analyze sentiment: "{text}"
    Classify: [Fear, Neutral, Greed]
    Score: -100(Fear) to 100(Greed)
    Output format: Label:Label, Score:Number
    """
    try:
        response = model.generate_content(prompt)
        content = response.text
        
        label = "Neutral"
        score = 0
        
        if "Label:" in content:
            label = content.split("Label:")[1].split(",")[0].strip()
        if "Score:" in content:
            score_str = content.split("Score:")[1].strip()
            score = int(float(score_str)) # 小数が来ることもあるので対策
            
        return label, score
    except:
        return "Neutral", 0

# --- 4. デモデータ生成機能 ---
def generate_market_data():
    """市場の声をシミュレーションするデモデータ"""
    return [
        "Bitcoin just hit a new All Time High! This is insane! 🚀",
        "Ethereum gas fees are too high, I'm selling everything.",
        "Solana network is down again... frustrated.",
        "Just bought the dip. WAGMI! (We Are Gonna Make It)",
        "The market looks very bearish today, be careful.",
        "Crypto is the future of finance, holding forever.",
        "Panic selling everywhere, is this the end?",
        "DOGE is pumping hard right now! To the moon!"
    ]

# --- 5. メイン画面 UI ---
st.title("📊 Crypto Sentiment Dashboard")

# モード切替
mode = st.radio("データソース選択", ["🤖 デモモード (シミュレーション)", "📝 手動入力"], horizontal=True)

if mode == "🤖 デモモード (シミュレーション)":
    st.info("実際のAPI制限を回避するため、仮想のSNS投稿データを生成して分析します。")
    
    if st.button("市場データを取得・分析開始 🔄", type="primary"):
        with st.spinner("SNSやニュースの声を収集中...(シミュレーション)"):
            # プログレスバー
            progress_bar = st.progress(0)
            
            raw_data = generate_market_data()
            results = []
            
            for i, text in enumerate(raw_data):
                label, score = analyze_text(text)
                results.append({"Text": text, "Label": label, "Score": score})
                time.sleep(0.5) # AIへの負荷軽減
                progress_bar.progress((i + 1) / len(raw_data))
            
            df = pd.DataFrame(results)
            
            # --- ダッシュボード表示 ---
            st.divider()
            
            # KPIカード
            avg_score = df['Score'].mean()
            col1, col2, col3 = st.columns(3)
            
            mood = "NEUTRAL"
            if avg_score > 20: mood = "GREED 🤑"
            elif avg_score < -20: mood = "FEAR 😱"
            
            with col1:
                st.markdown(f"<div class='metric-card'><h3>Market Mood</h3><h2 style='color:#bd00ff'>{mood}</h2></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div class='metric-card'><h3>Avg Score</h3><h2>{int(avg_score)}</h2></div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"<div class='metric-card'><h3>Analyzed Posts</h3><h2>{len(df)}</h2></div>", unsafe_allow_html=True)

            # グラフエリア
            c1, c2 = st.columns([2, 1])
            with c1:
                # 散布図
                fig = px.bar(df, x="Score", y="Text", orientation='h', color="Score", 
                             color_continuous_scale='RdYlGn', title="Individual Post Sentiment")
                fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                fig.update_yaxes(showticklabels=False) # テキストが長いので隠す
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                # 円グラフ
                fig_pie = px.pie(df, names="Label", title="Sentiment Distribution", 
                                 color_discrete_map={'Fear':'red', 'Greed':'green', 'Neutral':'gray'})
                fig_pie.update_layout(paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_pie, use_container_width=True)

            # 詳細データテーブル
            st.subheader("📋 分析データ一覧")
            st.dataframe(df)

else:
    # 手動入力モード（テスト用）
    user_input = st.text_area("分析したいテキストを入力", "BTC is going up!")
    if st.button("分析"):
        l, s = analyze_text(user_input)
        st.write(f"結果: **{l}** (スコア: {s})")