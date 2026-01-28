import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="Titan Income Projector", layout="wide", page_icon="💸")

st.markdown("""
<style>
    /* 全体設定 */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a0b2e 0%, #000000 70%);
        color: #e0e0e0;
    }
    
    /* 入力エリア */
    .stSlider > div > div > div > div { background-color: #00e5ff; }
    
    /* ガラスカード */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(0, 229, 255, 0.2);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 0 20px rgba(0, 229, 255, 0.1);
        text-align: center;
        transition: transform 0.3s;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .glass-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.3);
        border-color: #fff;
    }
    
    /* KPIテキスト */
    .kpi-label {
        font-size: 0.9rem;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 10px;
    }
    .kpi-value {
        font-size: 2.2rem;
        font-weight: 800;
        color: #fff;
        text-shadow: 0 0 10px rgba(0, 229, 255, 0.5);
    }
    .kpi-sub { font-size: 0.8rem; color: #ccc; margin-top: 5px; }

    /* プログレスバー風装飾 */
    .metric-bar {
        height: 4px;
        width: 100%;
        background: #333;
        margin-top: 10px;
        border-radius: 2px;
        overflow: hidden;
    }
    .metric-fill {
        height: 100%;
        background: linear-gradient(90deg, #00e5ff, #bd00ff);
    }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #00e5ff, #0099ff);
        border: none;
        color: black;
        font-weight: bold;
        padding: 15px 30px;
        border-radius: 30px;
        width: 100%;
        font-size: 1.2rem;
        transition: 0.3s;
        text-transform: uppercase;
    }
    .stButton > button:hover {
        box-shadow: 0 0 30px rgba(0, 229, 255, 0.6);
        transform: scale(1.02);
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Logic: Income Simulator ---

def calculate_roi(account_size, fee, monthly_return_pct, profit_split_pct, current_salary):
    """
    ROIと給与代替率を計算する
    """
    monthly_profit = account_size * (monthly_return_pct / 100)
    trader_payout = monthly_profit * (profit_split_pct / 100)
    
    # ROI (回収率)
    roi_percent = (trader_payout / fee * 100) if fee > 0 else 0
    payback_months = fee / trader_payout if trader_payout > 0 else float('inf')
    
    # 給与代替率
    salary_replacement = (trader_payout / current_salary * 100) if current_salary > 0 else 0
    
    # 年収換算
    annual_payout = trader_payout * 12
    
    return {
        "monthly_payout": trader_payout,
        "annual_payout": annual_payout,
        "roi_percent": roi_percent,
        "payback_months": payback_months,
        "salary_replacement": salary_replacement
    }

# --- 3. Main UI ---

st.title("💸 TITAN INCOME PROJECTOR")
st.markdown("<h4 style='color:#888;'>VISUALIZE YOUR FINANCIAL FREEDOM // NO SCALING REQUIRED</h4>", unsafe_allow_html=True)

# 入力セクション
c_input, c_result = st.columns([1, 2])

with c_input:
    st.subheader("🛠️ CONFIGURE YOUR ENGINE")
    
    # 口座サイズと参加費の目安
    account_options = {
        5000: 49,
        10000: 99,
        25000: 199,
        50000: 299,
        100000: 499,
        200000: 949
    }
    
    selected_size = st.selectbox(
        "Select Account Size", 
        options=list(account_options.keys()), 
        index=4,
        format_func=lambda x: f"${x:,.0f} Account"
    )
    
    # 参加費の手動調整（セールなどで変わるため）
    fee = st.number_input("Challenge Fee ($)", value=account_options[selected_size], step=10)
    
    st.markdown("---")
    
    # パフォーマンス設定
    monthly_return = st.slider("Target Monthly Return (%)", 1.0, 15.0, 4.0, 0.5)
    profit_split = st.slider("Profit Split (%)", 50, 95, 80, 5)
    
    # 現在の収入（比較用）
    current_salary = st.number_input("Current Monthly Salary ($)", value=3000, step=500)

# 計算実行
res = calculate_roi(selected_size, fee, monthly_return, profit_split, current_salary)

with c_result:
    # メインKPI
    k1, k2, k3 = st.columns(3)
    
    with k1:
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">MONTHLY PAYOUT</div>
            <div class="kpi-value" style="color:#00ff99;">${res['monthly_payout']:,.0f}</div>
            <div class="kpi-sub">Cash in Hand</div>
        </div>""", unsafe_allow_html=True)
        
    with k2:
        # 回収期間の表示ロジック
        if res['payback_months'] < 1:
            payback_text = "⚡ Instant (< 1 Mo)"
            payback_color = "#00e5ff"
        else:
            payback_text = f"{res['payback_months']:.1f} Months"
            payback_color = "#fff"
            
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">FEE PAYBACK</div>
            <div class="kpi-value" style="color:{payback_color};">{payback_text}</div>
            <div class="kpi-sub">ROI: {res['roi_percent']:.0f}%</div>
        </div>""", unsafe_allow_html=True)
        
    with k3:
        # 給与代替率
        rep_color = "#bd00ff" if res['salary_replacement'] >= 100 else "#e0e0e0"
        st.markdown(f"""
        <div class="glass-card">
            <div class="kpi-label">SALARY REPLACEMENT</div>
            <div class="kpi-value" style="color:{rep_color};">{res['salary_replacement']:.0f}%</div>
            <div class="kpi-sub">of your current job</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # グラフエリア：ROIの視覚化
    c_chart1, c_chart2 = st.columns([1, 1])
    
    with c_chart1:
        st.subheader("💰 The Power of Leverage")
        st.caption("Initial Fee vs. 1st Year Potential Income")
        
        # 比較データの作成
        comp_df = pd.DataFrame({
            "Category": ["Challenge Fee", "1 Year Payouts"],
            "Amount": [fee, res['annual_payout']],
            "Color": ["#ff0055", "#00ff99"]
        })
        
        fig = px.bar(comp_df, x="Amount", y="Category", orientation='h', text="Amount", color="Category", 
                     color_discrete_map={"Challenge Fee": "#555", "1 Year Payouts": "#00ff99"})
        
        fig.update_traces(texttemplate='$%{text:,.0f}', textposition='outside')
        fig.update_layout(paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='#e0e0e0', 
                          showlegend=False, height=250, margin=dict(l=0,r=50,t=0,b=0),
                          xaxis=dict(showgrid=False, visible=False))
        st.plotly_chart(fig, use_container_width=True)

    with c_chart2:
        st.subheader("🚀 Freedom Gauge")
        st.caption(f"Can you quit your job with a ${selected_size:,.0f} account?")
        
        fig_gauge = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = res['salary_replacement'],
            number = {'suffix': "%"},
            title = {'text': "Income Coverage"},
            gauge = {
                'axis': {'range': [0, 200], 'tickwidth': 1},
                'bar': {'color': "#00e5ff"},
                'bgcolor': "rgba(255,255,255,0.1)",
                'steps': [
                    {'range': [0, 50], 'color': "#333"},
                    {'range': [50, 100], 'color': "#555"},
                    {'range': [100, 200], 'color': "rgba(0, 229, 255, 0.2)"}],
                'threshold': {
                    'line': {'color': "#bd00ff", 'width': 4},
                    'thickness': 0.75,
                    'value': 100}
            }
        ))
        fig_gauge.update_layout(paper_bgcolor='rgba(0,0,0,0)', font={'color': "white"}, height=250, margin=dict(l=30,r=30,t=0,b=0))
        st.plotly_chart(fig_gauge, use_container_width=True)

# --- 4. Motivation Section ---
st.markdown("---")

# 具体的なイメージを植え付ける
items = [
    {"name": "iPhone 16 Pro", "price": 1200},
    {"name": "Luxury Watch", "price": 5000},
    {"name": "Dream Vacation", "price": 8000},
    {"name": "Tesla Model 3", "price": 40000}
]

can_buy = [item['name'] for item in items if res['annual_payout'] >= item['price']]
can_buy_str = ", ".join(can_buy) if can_buy else "Starting Small..."

st.markdown(f"""
<div style="text-align: center; padding: 20px;">
    <h2 style="background: linear-gradient(to right, #00ff99, #00e5ff); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        ROI: {res['roi_percent']:.0f}% in the 1st Month
    </h2>
    <p style="font-size: 1.2rem; color: #ccc; max-width: 800px; margin: 0 auto;">
        Stop risking your own savings. For just <b>${fee}</b>, you get access to <b>${selected_size:,.0f}</b>.
        <br>With just {monthly_return}% monthly performance, you generate <b>${res['monthly_payout']:,.0f} / month</b>.
        <br>That covers your fee in <b>{res['payback_months']:.1f} months</b>. Everything after that is pure profit.
    </p>
</div>
""", unsafe_allow_html=True)

# CTA
if st.button("⚡ START YOUR CAREER WITH SUPERFUNDED ⚡"):
    st.balloons()