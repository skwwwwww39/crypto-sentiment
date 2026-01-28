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
st.set_page_config(page_title="Crypto AI Sentiment 100", layout="wide", page_icon="⚡")

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
    /* グラフの説明文 */
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

# --- 3. データ取得 (100件取得のためのループ処理) ---
def get_bulk_news(limit=100):
    """CryptoPanicからページをめくって合計limit件取得する"""
    news_items = []
    page = 1
    
    # ブラウザ偽装ヘッダー
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36"}
    
    status_container = st.empty()
    
    try:
        while len(news_items) < limit:
            # 進行状況表示
            status_container.info(f"📥 Fetching data... {len(news_items)}/{limit} posts gathered.")
            
            url = f"https://cryptopanic.com/api/v1/posts/?auth_token={CRYPTOPANIC_API_KEY}&public=true&filter=rising&page={page}"
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                break
                
            data = response.json()
            if "results" not in data or not data["results"]:
                break
                
            for item in data["results"]:
                title = item["title"]
                published_at = item["created_at"]
                # 日付変換 (2024-01-29T12:00:00Z -> 2024-01-29 12:00)
                dt_obj = datetime.strptime(published_at, "%Y-%m-%dT%H:%M:%SZ")
                fmt_date = dt_obj.strftime("%Y-%m-%d %H:%M")
                
                news_items.append({
                    "id": len(news_items),
                    "text": title,
                    "date": fmt_date,
                    "source": item["domain"]
                })
                if len(news_items) >= limit:
                    break
            
            page += 1
            time.sleep(0.5) # APIへの配慮
            
        status_container.empty()
        return news_items
        
    except Exception as e:
        status_container.error(f"Connection Error: {e}")
        return []

# --- 4. バッチ分析 (高速化) ---
def analyze_batch(news_list):
    """20件ずつまとめてAIに分析させる"""
    if not api_key: return []
    
    results = []
    chunk_size = 20
    total_chunks = math.ceil(len(news_list) / chunk_size)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(news_list), chunk_size):
        chunk = news_list[i:i + chunk_size]
        current_chunk_num = (i // chunk_size) + 1
        
        status_text.markdown(f"🧠 Neural Analysis in progress... **Batch {current_chunk_num}/{total_chunks}**")
        
        # 複数のニュースを箇条書きで渡す
        news_text_block = "\n".join([f"{item['id']}: {item['text']}" for item in chunk])
        
        prompt = f"""
        Analyze the sentiment of these crypto news headlines.
        Return a list of scores and labels.
        
        Format constraints:
        - Output ONLY raw lines: ID | Label | Score
        - Label must be one of: [Despair, Fear, Negative, Positive, Optimism, Euphoria]
        - Score must be integer: -100 (Despair) to 100 (Euphoria)
        
        Headlines:
        {news_text_block}
        """
        
        try:
            response = model.generate_content(prompt)
            lines = response.text.strip().split("\n")
            
            # AIの回答をパースして元の辞書に結合
            for line in lines:
                parts = line.split("|")
                if len(parts) == 3:
                    try:
                        n_id = int(parts[0].strip())
                        label = parts[1].strip()
                        score = int(parts[2].strip())
                        
                        # IDでマッチング
                        for item in chunk:
                            if item['id'] == n_id:
                                item['Label'] = label
                                item['Score'] = score
                                results.append(item)
                    except:
                        continue
        except Exception as e:
            print(f"Error in batch: {e}")
        
        progress_bar.progress(current_chunk_num / total_chunks)
        time.sleep(1) # Rate limit回避

    status_text.empty()
    progress_bar.empty()
    return results

# --- シミュレーションデータ生成（API失敗時用） ---
def generate_mock_100():
    data = []
    import random
    sources = ["CoinDesk", "CoinTelegraph", "Twitter", "Reddit"]
    for i in range(100):
        score = random.randint(-80, 80)
        label = "Neutral"
        if score > 60: label = "Euphoria"
        elif score > 20: label = "Optimism"
        elif score > 0: label = "Positive"
        elif score > -20: label = "Negative"
        elif score > -60: label = "Fear"
        else: label = "Despair"
        
        data.append({
            "text": f"Simulation News Packet #{i} - Market movement detected",
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "source": random.choice(sources),
            "Label": label,
            "Score": score
        })
    return data

# --- 5. メインUI ---
st.title("⚡ Cyberpunk Sentiment Core (100x)")
st.markdown("Analysis of the last **100** market signals.")

if st.button("SCAN MARKET (100 POSTS) 🔄", type="primary"):
    
    # 1. データ取得
    raw_news = get_bulk_news(limit=100)
    
    # データが取れなかったらシミュレーション
    if not raw_news:
        st.warning("⚠️ Live feed offline. Generating 100 simulation nodes.")
        analyzed_data = generate_mock_100()
    else:
        # 2. AI分析
        analyzed_data = analyze_batch(raw_news)
        # マッチング漏れがあった場合の補正
        if len(analyzed_data) == 0:
            st.error("AI Analysis failed. Showing simulation.")
            analyzed_data = generate_mock_100()

    df = pd.DataFrame(analyzed_data)

    # --- 分析結果表示 ---
    st.divider()
    
    # 期間表示
    if not df.empty:
        dates = pd.to_datetime(df['date'])
        period_str = f"{dates.min().strftime('%m/%d %H:%M')} 〜 {dates.max().strftime('%m/%d %H:%M')}"
        st.markdown(f"<div style='text-align:center; color:#888; margin-bottom:20px;'>Data Period: {period_str}</div>", unsafe_allow_html=True)

    # KPI計算
    avg_score = df['Score'].mean()
    if avg_score >= 60: mood, color = "EUPHORIA 🚀", "#00FF99"
    elif avg_score >= 20: mood, color = "OPTIMISM 📈", "#00e5ff"
    elif avg_score <= -60: mood, color = "DESPAIR 💀", "#ff0055"
    elif avg_score <= -20: mood, color = "FEAR 😱", "#ff5e00"
    else: mood, color = "NEUTRAL 😐", "#bd00ff"

    # KPIカード
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
            <div class="metric-label">Data Points</div>
            <div class="metric-value">{len(df)}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # --- グラフエリア (説明付き) ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("📊 Sentiment Spectrum")
        st.markdown("<div class='chart-desc'>個々のニュースの感情スコア分布。<br>左に行くと「悲観（売り）」、右に行くと「楽観（買い）」を表します。</div>", unsafe_allow_html=True)
        
        # 散布図的バーチャート
        fig_bar = px.bar(
            df, 
            x="Score", 
            y="source", # Y軸をソースにして分散させる
            color="Score",
            hover_data=["text"],
            orientation='h',
            color_continuous_scale=['#ff0055', '#bd00ff', '#00e5ff', '#00FF99'],
            range_x=[-100, 100],
            title=""
        )
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            font_color='#e0c0ff',
            xaxis_title="← Bearish (Fear/Despair) ------------------ Bullish (Optimism/Euphoria) →",
            yaxis={'visible': False} # ごちゃつくので隠す
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.subheader("🥧 Emotion Ratio")
        st.markdown("<div class='chart-desc'>市場全体の感情比率。<br>どの感情が支配的かを確認します。</div>", unsafe_allow_html=True)
        
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
            legend=dict(orientation="h", y=-0.1) # 凡例を下にする
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # 生データ
    with st.expander(f"📋 View All {len(df)} Analyzed Logs"):
        st.dataframe(df, use_container_width=True)