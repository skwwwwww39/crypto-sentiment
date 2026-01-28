import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="The Smart Switch: FX vs Prop", layout="wide", page_icon="⚡")

st.markdown("""
<style>
    /* 全体設定 */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #0d1b2a 0%, #000000 80%);
        color: #e0e0e0;
    }
    
    /* 入力エリア */
    .stSlider > div > div > div > div { background-color: #bd00ff; }
    
    /* カードデザイン */
    .glass-card {
        background: rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(189, 0, 255, 0.2);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        text-align: center;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .winner-card { border: 2px solid #00ff99; box-shadow: 0 0 20px rgba(0, 255, 153, 0.2); }
    .loser-card { border: 1px solid #555; opacity: 0.8; }
    
    .kpi-label { font-size: 0.8rem; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 2.0rem; font-weight: 800; color: #fff; }
    .kpi-sub { font-size: 0.9rem; margin-top: 5px; color: #ccc; }
    
    /* ボタン */
    .stButton > button {
        background: linear-gradient(90deg, #bd00ff, #00e5ff);
        border: none;
        color: white;
        font-weight: bold;
        padding: 15px 30px;
        border-radius: 30px;
        width: 100%;
        font-size: 1.2rem;
        transition: 0.3s;
        text-transform: uppercase;
    }
    .stButton > button:hover {
        box-shadow: 0 0 30px rgba(189, 0, 255, 0.6);
        transform: scale(1.02);
    }
    
    /* 警告ボックス */
    .risk-box {
        background: rgba(255, 0, 85, 0.1);
        border-left: 4px solid #ff0055;
        padding: 15px;
        margin-top: 20px;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# --- 2. Logic: Comparative Simulation ---

def calculate_comparison(budget_jpy, monthly_roi, failures_before_pass, prop_account_dollars, prop_fee_dollars, exchange_rate=150):
    """
    比較シミュレーションロジック
    """
    # 通貨変換
    prop_fee_jpy = prop_fee_dollars * exchange_rate
    prop_size_jpy = prop_account_dollars * exchange_rate
    
    # --- A. 個人口座 (Overseas FX) ---
    # 予算全額を口座に入れてスタート
    personal_equity = budget_jpy
    personal_data = []
    personal_total_profit = 0
    
    # 12ヶ月シミュレーション
    for m in range(1, 13):
        profit = personal_equity * (monthly_roi / 100)
        personal_total_profit += profit
        personal_equity += profit # 複利運用と仮定
        personal_data.append(personal_total_profit)

    # --- B. プロップファーム (SuperFunded) ---
    # ハードル計算: 試験費用と期間
    total_cost = prop_fee_jpy * (1 + failures_before_pass) # 合格するまでにかかった費用
    
    # 予算オーバーチェック
    if total_cost > budget_jpy:
        return None, f"予算不足です。チャレンジ{failures_before_pass+1}回分の費用 ({total_cost:,.0f}円) が足りません。"
    
    # 試験期間 (1回あたり平均1.5ヶ月かかると仮定 + 失敗回数分)
    # 合格回(1回) = Phase1(1ヶ月) + Phase2(1ヶ月) = 2ヶ月無報酬
    # 失敗回(N回) = 平均1ヶ月で失敗すると仮定
    months_delayed = (failures_before_pass * 1) + 2 
    
    prop_data = []
    prop_total_pocket = -total_cost # スタートはマイナス（参加費分）
    
    for m in range(1, 13):
        if m <= months_delayed:
            # まだ試験中 or 失敗中（利益ゼロ）
            prop_data.append(prop_total_pocket)
        else:
            # 合格後（運用開始）
            # 利益分配 (80%と仮定)
            gross_profit = prop_size_jpy * (monthly_roi / 100)
            payout = gross_profit * 0.8
            prop_total_pocket += payout
            prop_data.append(prop_total_pocket)
            
    return {
        "personal": personal_data,
        "prop": prop_data,
        "months_delayed": months_delayed,
        "cost": total_cost,
        "prop_size_jpy": prop_size_jpy
    }, None

# --- 3. Main UI ---

st.title("⚡ THE SMART SWITCH")
st.markdown("<h4 style='color:#aaa;'>STOP GAMBLING YOUR SAVINGS. START MANAGING CAPITAL.</h4>", unsafe_allow_html=True)

# サイドバー入力
with st.sidebar:
    st.header("📊 YOUR REALITY")
    
    budget = st.number_input("Your Trading Budget (JPY)", value=100000, step=10000, help="失ってもいい手持ち資金")
    
    monthly_roi = st.slider("Your Skill (Monthly Return %)", 1.0, 20.0, 5.0, 0.5, help="現実的な月利")
    
    st.markdown("---")
    st.header("🏆 PROP CHALLENGE")
    
    # 口座サイズ選択
    account_options = {
        5000: 49,
        10000: 99,
        25000: 199,
        50000: 299,
        100000: 499
    }
    selected_acc = st.selectbox("Target Account Size ($)", list(account_options.keys()), index=1, format_func=lambda x: f"${x:,}")
    fee_usd = account_options[selected_acc]
    
    st.markdown(f"**Challenge Fee: ${fee_usd}**")
    
    # ★ここが重要：ハードルを加味
    failures = st.slider("Expected Failures before Passing", 0, 5, 1, help="何回落ちてから受かる想定ですか？正直に設定してください。")
    
    st.markdown("---")
    st.caption("Exchange Rate: 1 USD = 150 JPY")

# 計算実行
res, error = calculate_comparison(budget, monthly_roi, failures, selected_acc, fee_usd)

if error:
    st.error(error)
else:
    # 結果データの整形
    df = pd.DataFrame({
        "Month": range(1, 13),
        "Personal FX (Own Cash)": res['personal'],
        "SuperFunded (Prop Firm)": res['prop']
    })
    
    final_personal = res['personal'][-1]
    final_prop = res['prop'][-1]
    
    # ROI倍率
    roi_multiple = final_prop / final_personal if final_personal > 0 else 0
    
    # --- ROW 1: THE TRUTH ---
    c1, c2, c3 = st.columns([1, 1, 1])
    
    with c1:
        st.markdown(f"""
        <div class="glass-card loser-card">
            <div class="kpi-label">TRADING YOUR {budget:,} JPY</div>
            <div class="kpi-value" style="color:#aaa;">¥{final_personal:,.0f}</div>
            <div class="kpi-sub">Total Profit after 1 Year</div>
        </div>""", unsafe_allow_html=True)
        
    with c2:
         st.markdown(f"""
        <div class="glass-card" style="border:none; background:transparent; box-shadow:none;">
            <div style="font-size:1rem; color:#888;">THE DIFFERENCE</div>
            <div style="font-size:3.5rem; font-weight:900; color:#00ff99; text-shadow:0 0 20px #00ff99;">{roi_multiple:.1f}x</div>
            <div style="font-size:0.8rem; color:#ccc;">More Cash in Pocket</div>
        </div>""", unsafe_allow_html=True)
        
    with c3:
        st.markdown(f"""
        <div class="glass-card winner-card">
            <div class="kpi-label">TRADING PROP (AFTER {failures} FAILS)</div>
            <div class="kpi-value" style="color:#00ff99;">¥{final_prop:,.0f}</div>
            <div class="kpi-sub">Total Payout after 1 Year</div>
        </div>""", unsafe_allow_html=True)

    # --- ROW 2: RISK ANALYSIS ---
    st.markdown(f"""
    <div class="risk-box">
        <h3 style="margin:0; color:#ff0055;">⚠️ RISK REALITY CHECK</h3>
        <p style="font-size:1.1rem; margin-top:10px;">
            If you trade your own <b>¥{budget:,}</b> on High Leverage FX and blow up (95% chance), you lose <b>¥{budget:,}</b>.<br>
            If you fail the SuperFunded challenge {failures} times, you lose <b>¥{res['cost']:,}</b> (Fees).<br>
            <br>
            <b>Result:</b> The financial risk is similar, but the upside potential with SuperFunded is <b>{roi_multiple:.1f} times higher</b>.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- ROW 3: VISUALIZATION ---
    st.subheader("📈 Profit Trajectory (1 Year)")
    
    fig = go.Figure()
    
    # Personal Line
    fig.add_trace(go.Scatter(
        x=df['Month'], y=df['Personal FX (Own Cash)'],
        mode='lines+markers', name='Personal FX',
        line=dict(color='#888', width=2, dash='dash')
    ))
    
    # Prop Line
    fig.add_trace(go.Scatter(
        x=df['Month'], y=df['SuperFunded (Prop Firm)'],
        mode='lines+markers', name='SuperFunded',
        line=dict(color='#00ff99', width=4)
    ))
    
    # Annotation for Evaluation Phase
    if res['months_delayed'] < 12:
        fig.add_vrect(
            x0=0, x1=res['months_delayed'],
            fillcolor="red", opacity=0.1,
            layer="below", line_width=0,
            annotation_text="EVALUATION HURDLE", annotation_position="top left",
            annotation_font_color="#ff0055"
        )
    
    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font_color='#ccc', height=450,
        xaxis=dict(showgrid=False, title="Months"),
        yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', title="Net Profit (JPY)"),
        legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- CTA ---
    st.markdown("---")
    st.markdown(f"""
    <div style="text-align:center; padding:20px;">
        <h2>Ready to make the switch?</h2>
        <p style="color:#aaa;">Stop risking your savings for pennies. Pass the evaluation, unlock the capital.</p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔥 START CHALLENGE (Risk: Fees Only) 🔥"):
        st.balloons()