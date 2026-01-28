import streamlit as st
import pandas as pd
import plotly.express as px
import pdfplumber
import re

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="Titan Analytics: SuperFunded", layout="wide", page_icon="🛡️")

st.markdown("""
<style>
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a0b2e 0%, #000000 60%);
        color: #e0e0e0;
    }
    .glass-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .kpi-label { font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 2.0rem; font-weight: 800; color: #fff; }
    .stFileUploader > div > div {
        background-color: rgba(255, 255, 255, 0.05);
        border: 1px dashed #bd00ff;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Robust Parsing Engine ---

def clean_cell_text(text):
    """セル内の改行や汚れを除去して、最初の有効な行だけ取る"""
    if not text: return ""
    # 改行で分割して、空じゃない最初の行を取る
    lines = str(text).split('\n')
    for line in lines:
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""

def clean_currency(value):
    """通貨形式 ($1,234.56) を float に変換"""
    if isinstance(value, (int, float)): return float(value)
    s = str(value)
    # OCRノイズ除去 (5-284 -> -284, $除去, ,除去)
    s = s.replace('$', '').replace(',', '').replace(' ', '')
    s = re.sub(r'^[45]-', '-', s) # "5-100" みたいなOCRミスを "-100" に
    try:
        return float(s)
    except:
        return 0.0

def parse_pdf(file):
    """SuperFunded PDFパーサー (汚れたデータ対応版)"""
    data = []
    
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                for table in tables:
                    for row in table:
                        # 行全体をクリーニング（改行などを除去）
                        clean_row = [clean_cell_text(cell) for cell in row]
                        
                        # データ行判定ロジック（緩和版）
                        # 条件: 列数が十分あり、2列目か3列目に "Buy" か "Sell" が含まれているか
                        # または、1列目がIDっぽい（長い数字）か
                        if len(clean_row) >= 8:
                            # IDチェック (数字のみ抽出して10桁以上あるか)
                            id_digits = "".join(filter(str.isdigit, clean_row[0]))
                            is_id = len(id_digits) > 10
                            
                            # タイプチェック
                            type_col = clean_row[2].lower()
                            is_trade = 'buy' in type_col or 'sell' in type_col
                            
                            if is_id or is_trade:
                                try:
                                    item = {
                                        "Open Time": clean_row[1],
                                        "Type": clean_row[2],
                                        "Symbol": clean_row[3],
                                        "Net Profit": clean_currency(clean_row[-1])
                                    }
                                    data.append(item)
                                except:
                                    continue

        if not data:
            return pd.DataFrame()

        df = pd.DataFrame(data)
        
        # 日付変換 (失敗したらNaTになるがエラーで止まらないようにする)
        df['Open Time'] = pd.to_datetime(df['Open Time'], dayfirst=True, errors='coerce')
        
        # 日付が取れなかった行（ゴミ行）を削除
        df = df.dropna(subset=['Open Time'])
        
        return df

    except Exception as e:
        st.error(f"解析エラー: {e}")
        return pd.DataFrame()

def load_demo_data():
    """デモデータ生成"""
    dates = pd.date_range(end=pd.Timestamp.now(), periods=30, freq='D')
    df = pd.DataFrame({
        "Open Time": dates,
        "Symbol": ["USDJPY", "EURUSD", "GBPUSD", "XAUUSD", "BTCUSD"] * 6,
        "Type": ["Buy", "Sell"] * 15,
        "Net Profit": [100, -50, 200, -120, 300, -80, 50, -200, 400, -100] * 3
    })
    return df

# --- 3. Analytics Logic ---

def analyze_data(df):
    if df.empty: return None
    
    total_trades = len(df)
    total_pnl = df['Net Profit'].sum()
    wins = df[df['Net Profit'] > 0]
    losses = df[df['Net Profit'] <= 0]
    
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    profit_factor = (wins['Net Profit'].sum() / abs(losses['Net Profit'].sum())) if not losses.empty else float('inf')
    
    # 累積損益カーブ用
    df_sorted = df.sort_values('Open Time')
    df_sorted['Cumulative PnL'] = df_sorted['Net Profit'].cumsum()
    
    # 曜日別集計
    df['Day'] = df['Open Time'].dt.day_name()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    # 存在しない曜日も0埋めするためにreindex
    day_pnl = df.groupby('Day')['Net Profit'].sum().reindex(day_order).fillna(0).reset_index()

    return {
        "df": df_sorted,
        "total_trades": total_trades,
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
        "day_pnl": day_pnl
    }

# --- 4. Dashboard UI ---

st.title("🛡️ TITAN ANALYTICS")
st.markdown("SUPERFUNDED JOURNAL // PDF PARSER")

with st.sidebar:
    st.header("📂 DATA INPUT")
    uploaded_file = st.file_uploader("Upload PDF Report", type="pdf")
    use_demo = st.checkbox("Demo Mode", value=False)
    st.info("SuperFundedの取引履歴PDFをアップロードしてください。")

df = pd.DataFrame()

if uploaded_file:
    with st.spinner("Analyzing PDF..."):
        df = parse_pdf(uploaded_file)
        if df.empty:
            st.error("PDFからデータを読み取れませんでした。ファイル形式を確認するか、デモモードをお試しください。")
elif use_demo:
    df = load_demo_data()

if not df.empty:
    m = analyze_data(df)
    
    # KPI Row
    c1, c2, c3, c4 = st.columns(4)
    p_col = "#00ff99" if m['total_pnl'] >= 0 else "#ff0055"
    
    c1.markdown(f"<div class='glass-card'><div class='kpi-label'>NET PROFIT</div><div class='kpi-value' style='color:{p_col}'>${m['total_pnl']:,.2f}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='glass-card'><div class='kpi-label'>WIN RATE</div><div class='kpi-value'>{m['win_rate']:.1f}%</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='glass-card'><div class='kpi-label'>PROFIT FACTOR</div><div class='kpi-value'>{m['profit_factor']:.2f}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='glass-card'><div class='kpi-label'>TRADES</div><div class='kpi-value'>{m['total_trades']}</div></div>", unsafe_allow_html=True)

    # Charts
    st.subheader("📈 Equity Curve")
    fig_eq = px.area(m['df'], x='Open Time', y='Cumulative PnL')
    fig_eq.update_traces(line_color='#00e5ff', fillcolor='rgba(0, 229, 255, 0.1)')
    fig_eq.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#888', height=350, margin=dict(t=0,b=0,l=0,r=0))
    st.plotly_chart(fig_eq, use_container_width=True)

    c_left, c_right = st.columns(2)
    with c_left:
        st.subheader("📅 PnL by Day")
        fig_day = px.bar(m['day_pnl'], x='Day', y='Net Profit', color='Net Profit', color_continuous_scale=['#ff0055', '#333', '#00ff99'])
        fig_day.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#888', height=300, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_day, use_container_width=True)
    
    with c_right:
        st.subheader("📊 Symbol Performance")
        sym_pnl = df.groupby('Symbol')['Net Profit'].sum().sort_values()
        fig_sym = px.bar(x=sym_pnl.values, y=sym_pnl.index, orientation='h', color=sym_pnl.values, color_continuous_scale=['#ff0055', '#333', '#00ff99'])
        fig_sym.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#888', height=300, margin=dict(t=0,b=0,l=0,r=0))
        st.plotly_chart(fig_sym, use_container_width=True)

    with st.expander("Show Raw Data"):
        st.dataframe(m['df'][['Open Time', 'Symbol', 'Type', 'Net Profit']].sort_values('Open Time', ascending=False), use_container_width=True)

else:
    # 待機画面
    st.markdown("<div style='text-align:center; padding:50px; opacity:0.6'><h1>READY TO ANALYZE</h1><p>Upload your PDF from the sidebar.</p></div>", unsafe_allow_html=True)