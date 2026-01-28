import streamlit as st
import pandas as pd
import plotly.express as px
import google.generativeai as genai
import os
import time
import requests
import math
from datetime import datetime

# --- 1. デザイン設定 (Cyberpunk UI) ---
st.set_page_config(page_title="Real Crypto Sentiment", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    .stApp {
        background: radial-gradient(circle at center top, #1a0b2e 0%, #000000 100%);
        color: #e0e0e0;
    }
    /* カードデザイン */
    .metric-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(189, 0, 255, 0.2);
        backdrop-filter: blur(10px);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        text-shadow: 0 0 10px rgba(0, 229, 255, 0.6);
        color: #fff;
    }
    .metric-label {
        color: #b39ddb;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    .chart-desc {
        font-size: 0.8rem;
        color: #888;
        text-align: center;
        margin-bottom: 5px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. API設定 ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except:
    api_key = os.getenv("GEMINI_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-flash-latest')

CRYPTOPANIC_API_KEY = "ce5d1a3effe7a877dcf19adbce33ef35ded05f5e"

# --- 3. データ取得 (リトライ強化・シミュレーション廃止) ---
def get_bulk_news_real_only(limit=50):
    """
    CryptoPanicからページをめくってデータを取得する。
    シミュレーションは一切行わない。
    """
    news_items = []
    page = 1
    max_retries = 3 # 失敗しても3回までは粘る
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
    
    status_container = st.empty()
    
    while len(news_items) < limit:
        status_container.info(f"📥 Fetching REAL data from page {page}... ({len(news_items)}/{limit})")
        
        url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&public=true&filter=rising&page={page}"
        
        success = False
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    success = True
                    break
                else:
                    time.sleep(2) # エラーなら少し待ってリトライ
            except Exception:
                time.sleep(2)
        
        if not success:
            st.warning(f"Page {page} could not be fetched. Stopping here.")
            break
            
        data = response.json()
        if "results" not in data or not data["results"]:
            break # もうデータがない
            
        for item in data["results"]:
            title = item["title"]
            published_at = item["created_at"]
            # 日付変換
            try:
                dt_obj = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                fmt_date = dt_obj.strftime("%Y-%m-%d %H:%M")
            except:
                fmt_date = published_at
            
            # ソースフィルタ（Botっぽいソースを除外して質を高める）
            domain = item.get("domain", "Unknown")
            
            news_items.append({
                "id": len(news_items),
                "text": title,
                "date": fmt_date,
                "source": domain
            })
            if len(news_items) >= limit:
                break
        
        page += 1
        time.sleep(1.0) # API制限にかからないよう、あえてゆっくり取得
        
    status_container.empty()
    return news_items

# --- 4. バッチ分析 ---
def analyze_batch(news_list):
    """20件ずつまとめてAIに分析させる"""
    if not api_key: return []
    if not news_list: return []
    
    results = []
    chunk_size = 20
    total_chunks = math.ceil(len(news_list) / chunk_size)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(news_list), chunk_size):
        chunk = news_list[i:i + chunk_size]
        current_chunk_num = (i // chunk_size) + 1
        
        status_text.markdown(f"🧠 AI Analyzing real data... **Batch {current_chunk_num}/{total_chunks}**")
        
        news_text_block = "\n".join([f"{item['id']}: {item['text']}" for item in chunk])
        
        prompt = f"""
        Analyze sentiment of these crypto news.
        Format: ID | Label | Score
        Label: [Despair, Fear, Negative, Positive, Optimism, Euphoria]
        Score: -100 to 100
        Data:
        {news_text_block}
        """
        
        try:
            response = model.generate_content(prompt)
            lines = response.text.strip().split("\n")
            
            for line in lines:
                parts = line.split("|")
                if len(parts) == 3:
                    try:
                        n_id = int(parts[0].strip())
                        label = parts[1].strip()
                        score = int(parts[2].strip())
                        
                        for item in chunk:
                            if item['id'] == n_id:
                                item['Label'] = label
                                item['Score'] = score
                                results.append(item)
                    except:
                        continue
        except Exception as e:
            print(f"Batch Error: {e}")
        
        progress_bar.progress(current_chunk_num / total_chunks)
        time.sleep(1) 

    status_text.empty()
    progress_bar.empty()
    return results

# --- 5. メインUI ---
st.title("⚡ Real-Time Sentiment (No Simulation)")
st.markdown("Fetching only **REAL** market data. This may take a moment.")

# ボタン
if st.button("FETCH REAL DATA 🔄", type="primary"):
    
    # 1. データ取得（ここが成功しないと何も表示しない）
    raw_news = get_bulk_news_real_only(limit=60) # 確実性を高めるため一旦60件に設定
    
    if not raw_news:
        st.error("❌ Failed to fetch real data. Please try again in a few minutes.")
    else:
        # 2. AI分析
        analyzed_data = analyze_batch(raw_news)
        
        if len(analyzed_data) == 0:
            st.error("❌ AI Analysis failed. Please check API Key.")
        else:
            df = pd.DataFrame(analyzed_data)

            # --- 結果表示 ---
            st.divider()
            
            # 期間表示
            dates = pd.to_datetime(df['date'])
            period_str = f"{dates.min().strftime('%m/%d %H:%M')} 〜 {dates.max().strftime('%m/%d %H:%M')}"
            st.markdown(f"<div style='text-align:center; color:#888; margin-bottom:20px;'>Real Data Period: {period_str}</div>", unsafe_allow_html=True)

            # KPI
            avg_score = df['Score'].mean()
            if avg_score >= 60: mood, color = "EUPHORIA 🚀", "#00FF99"
            elif avg_score >= 20: mood, color = "OPTIMISM 📈", "#00e5ff"
            elif avg_score <= -60: mood, color = "DESPAIR 💀", "#ff0055"
            elif avg_score <= -20: mood, color = "FEAR 😱", "#ff5e00"
            else: mood, color = "NEUTRAL 😐", "#bd00ff"

            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Market Mood</div>
                    <div class="metric-value" style="color:{color}">{mood}</div>
                </div>""", unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Avg Sentiment Score</div>
                    <div class="metric-value">{int(avg_score)}</div>
                </div>""", unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-label">Real Posts Analyzed</div>
                    <div class="metric-value">{len(df)}</div>
                </div>""", unsafe_allow_html=True)

            st.markdown("---")

            # グラフエリア
            col_left, col_right = st.columns([2, 1])

            with col_left:
                st.subheader("📊 Sentiment Spectrum")
                st.markdown("<div class='chart-desc'>Real news sentiment distribution.<br>Left: Bearish | Right: Bullish</div>", unsafe_allow_html=True)
                
                fig_bar = px.bar(
                    df, 
                    x="Score", 
                    y="source", 
                    color="Score",
                    hover_data=["text"],
                    orientation='h',
                    color_continuous_scale=['#ff0055', '#bd00ff', '#00e5ff', '#00FF99'],
                    range_x=[-100, 100],
                )
                fig_bar.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(0,0,0,0)', 
                    font_color='#e0c0ff',
                    yaxis={'visible': False}
                )
                st.plotly_chart(fig_bar, use_container_width=True)

            with col_right:
                st.subheader("🥧 Emotion Ratio")
                color_map = {
                    "Euphoria": "#00FF99", "Optimism": "#00e5ff", 
                    "Positive": "#3498DB", "Neutral": "#bd00ff", 
                    "Negative": "#F1C40F", "Fear": "#ff5e00", "Despair": "#ff0055"
                }
                fig_pie = px.pie(
                    df, 
                    names="Label", 
                    hole=0.6, 
                    color="Label", 
                    color_discrete_map=color_map
                )
                fig_pie.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    font_color='#e0c0ff',
                    legend=dict(orientation="h", y=-0.1)
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with st.expander(f"📋 View All Real Data Logs"):
                st.dataframe(df, use_container_width=True)