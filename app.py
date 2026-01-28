import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import pdfplumber
import re
import io

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="Titan Analytics: SuperFunded", layout="wide", page_icon="📊")

st.markdown("""
<style>
    /* 全体設定 */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a0b2e 0%, #000000 60%);
        color: #e0e0e0;
    }
    
    /* カードデザイン */
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        text-align: center;
    }
    
    /* KPIテキスト */
    .kpi-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 2.0rem; font-weight: 800; color: #fff; }
    
    /* アップローダー */
    .stFileUploader > div > div {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px dashed #bd00ff;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Data Parsing Engine ---

def clean_currency(value):
    """通貨記号やOCRノイズを除去してfloatにする"""
    if isinstance(value, (int, float)): return float(value)
    if not isinstance(value, str): return 0.0
    
    # ノイズ除去 (5-284 -> -284, $除去, ,除去)
    val = value.replace('$', '').replace(',', '').replace(' ', '')
    val = re.sub(r'[45]-', '-', val) # OCRエラー対策: 5- や 4- をマイナスに置換
    
    try:
        return float(val)
    except:
        return 0.0

def parse_pdf(file):
    """SuperFundedのPDFからテーブルを抽出する"""
    all_rows = []
    
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                # テーブル抽出
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # ヘッダー行や空行をスキップする簡易ロジック
                        clean_row = [str(cell).strip() if cell else "" for cell in row]
                        # IDっぽい長さの列があるか確認
                        if len(clean_row) > 0 and len(clean_row[0]) > 10 and clean_row[0].isdigit():
                            all_rows.append(clean_row)
        
        # DataFrame化 (カラム位置はPDFの構造に合わせる)
        # 想定: [ID, OpenTime, Type, Symbol, CloseTime, Vol/Open, Close, Comm, Swap/Profit, NetProfit]
        # ※PDFの列結合状態によってズレる場合があるため、補正ロジックを入れる
        
        data = []
        for r in all_rows:
            # 必要なデータだけ抜き出して辞書にする
            # 注: PDFplumberの抽出結果に合わせて調整が必要
            # ここでは「Net Profit」が最後の列にあると仮定
            try:
                item = {
                    "Open Time": r[1],
                    "Type": r[2],
                    "Symbol": r[3],
                    "Net Profit": clean_currency(r[-1])
                }
                data.append(item)
            except:
                continue
                
        df = pd.DataFrame(data)
        
        # 日付変換
        df['Open Time'] = pd.to_datetime(df['Open Time'], errors='coerce', dayfirst=True)
        return df

    except Exception as e:
        st.error(f"Error parsing PDF: {e}")
        return pd.DataFrame()

# デモデータ生成（解析失敗時やテスト用）
def load_demo_data():
    data = {
        "Open Time": pd.date_range(start="2025-02-01", periods=50, freq="6H"),
        "Symbol": ["USDJPY"]*20 + ["XAUUSD"]*15 + ["BTCUSD"]*10 + ["EURUSD"]*5,
        "Type": ["Buy"]*25 + ["Sell"]*25,
        "Net Profit": [
            -286.08, -857.74, -1136.66, 1500.0, 2300.5, -500.0, 450.0, 
            -100.0, 890.0, -1200.0, 3000.0, -150.0, -150.0, 600.0, 100.0,
            -2000.0, 500.0, 500.0, -300.0, -300.0, 4000.0, -50.0, -50.0,
            1200.0, -800.0, 250.0, -400.0, 900.0, 900.0, -100.0, -200.0,
            5000.0, -2500.0, 150.0, 150.0, -600.0, 800.0, -50.0, -50.0,
            200.0, 200.0, -1000.0, 300.0, 300.0, -400.0, 500.0, 100.0, -50.0, 20.0, 0.0
        ]
    }
    df = pd.DataFrame(data)
    # 日付から曜日などを生成
    df['Day'] = df['Open Time'].dt.day_name()
    df['Hour'] = df['Open Time'].dt.hour
    return df

# --- 3. Analytics Logic ---

def analyze_data(df):
    if df.empty: return None
    
    # 基本KPI
    total_trades = len(df)
    total_pnl = df['Net Profit'].sum()
    wins = df[df['Net Profit'] > 0]
    losses = df[df['Net Profit'] <= 0]
    
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    avg_win = wins['Net Profit'].mean() if not wins.empty else 0
    avg_loss = losses['Net Profit'].mean() if not losses.empty else 0
    
    gross_profit = wins['Net Profit'].sum()
    gross_loss = abs(losses['Net Profit'].sum())
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0
    
    # 累積損益
    df = df.sort_values('Open Time')
    df['Cumulative PnL'] = df['Net Profit'].cumsum()
    
    # 曜日別分析
    df['Day'] = df['Open Time'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_pnl = df.groupby('Day')['Net Profit'].sum().reindex(day_order).fillna(0)
    
    return {
        "df": df,
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "day_pnl": day_pnl
    }

# --- 4. Main Dashboard UI ---

st.title("🛡️ TITAN ANALYTICS")
st.markdown("SUPERFUNDED TRADING JOURNAL // PDF PARSER")

# サイドバー：ファイルアップロード
with st.sidebar:
    st.header("📂 DATA SOURCE")
    uploaded_file = st.file_uploader("Upload Report (PDF)", type="pdf")
    
    use_demo = st.checkbox("Use Demo Data (No File)", value=False)
    
    st.markdown("---")
    st.markdown("""
    **Instructions:**
    1. Download 'Trading History' as PDF from SuperFunded portal.
    2. Upload the file here.
    3. Analyze your weak points.
    """)

# データ読み込み処理
df = pd.DataFrame()

if uploaded_file is not None:
    with st.spinner("Parsing PDF..."):
        df = parse_pdf(uploaded_file)
        if df.empty:
            st.warning("PDF parsing failed or empty. Try Demo Data.")
elif use_demo:
    df = load_demo_data()

# 分析実行
if not df.empty:
    metrics = analyze_data(df)
    
    # --- ROW 1: KPI CARDS ---
    c1, c2, c3, c4 = st.columns(4)
    
    pnl_color = "#00ff99" if metrics['total_pnl'] >= 0 else "#ff0055"
    
    with c1:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">NET PROFIT</div>
            <div class="kpi-value" style="color:{pnl_color}">${metrics['total_pnl']:,.2f}</div>
        </div>""", unsafe_allow_html=True)
        
    with c2:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">WIN RATE</div>
            <div class="kpi-value">{metrics['win_rate']:.1f}%</div>
        </div>""", unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">PROFIT FACTOR</div>
            <div class="kpi-value">{metrics['profit_factor']:.2f}</div>
        </div>""", unsafe_allow_html=True)
        
    with c4:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">TOTAL TRADES</div>
            <div class="kpi-value">{metrics['total_trades']}</div>
        </div>""", unsafe_allow_html=True)

    # --- ROW 2: EQUITY CURVE ---
    st.subheader("📈 Equity Curve (Cumulative PnL)")
    fig_equity = px.area(metrics['df'], x='Open Time', y='Cumulative PnL')
    fig_equity.update_traces(line_color='#00e5ff', fillcolor='rgba(0, 229, 255, 0.1)')
    fig_equity.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#888'), height=350, margin=dict(l=0,r=0,t=0,b=0),
        xaxis=dict(showgrid=False), yaxis=dict(gridcolor='rgba(255,255,255,0.1)')
    )
    st.plotly_chart(fig_equity, use_container_width=True)

    # --- ROW 3: DEEP DIVE ---
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("📅 PnL by Day of Week")
        # 曜日別損益グラフ
        day_data = metrics['day_pnl'].reset_index()
        fig_day = px.bar(day_data, x='Day', y='Net Profit', color='Net Profit',
                        color_continuous_scale=['#ff0055', '#333', '#00ff99'])
        fig_day.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#888'), height=300, margin=dict(l=0,r=0,t=0,b=0)
        )
        st.plotly_chart(fig_day, use_container_width=True)
        st.caption("Tip: Avoid trading on your red days.")

    with col_right:
        st.subheader("📊 Symbol Performance")
        # 通貨ペア別損益
        sym_pnl = metrics['df'].groupby('Symbol')['Net Profit'].sum().sort_values()
        fig_sym = px.bar(sym_pnl, x=sym_pnl.values, y=sym_pnl.index, orientation='h',
                        color=sym_pnl.values, color_continuous_scale=['#ff0055', '#333', '#00ff99'])
        fig_sym.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(color='#888'), height=300, margin=dict(l=0,r=0,t=0,b=0)
        )
        st.plotly_chart(fig_sym, use_container_width=True)

    # --- ROW 4: HISTORY TABLE ---
    with st.expander("📋 Detailed Trade Log"):
        st.dataframe(metrics['df'][['Open Time', 'Symbol', 'Type', 'Net Profit']].sort_values('Open Time', ascending=False), use_container_width=True)

else:
    # 待機画面
    st.info("👆 Upload your SuperFunded PDF report from the sidebar to initialize analysis.")
    st.markdown("""
    <div style='text-align: center; margin-top: 50px; opacity: 0.5;'>
        <h1>WAITING FOR DATA</h1>
        <p>No external connections. 100% Secure & Local Processing.</p>
    </div>
    """, unsafe_allow_html=True)