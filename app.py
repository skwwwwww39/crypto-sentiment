import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- 1. Cyberpunk Design System ---
st.set_page_config(page_title="The Smart Switch: CFD vs Prop", layout="wide", page_icon="⚡")

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
    .loser-card { border: 1px solid #ff0055; opacity: 0.8; }
    
    .kpi-label { font-size: 0.8rem; color: #aaa; text-transform: uppercase; letter-spacing: 1px; }
    .kpi-value { font-size: 2.0rem; font-weight: 800; color: #fff; }
    .kpi-sub { font-size: 0.9rem; margin-top: 5px; color: #ccc; }
    
    /* 危険ゾーン */
    .danger-zone {
        background: rgba(255, 0, 85, 0.05);
        border: 1px solid #ff0055;
        padding: 20px;
        border-radius: 10px;
        margin-top: 20px;
    }

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
</style>
""", unsafe_allow_html=True)

# --- 2. Simulation Logic ---

def run_simulation(budget, monthly_roi, failures, prop_acc_size, prop_fee):
    # A. CFD Personal Account (High Leverage / Own Risk)
    personal_data = []
    personal_balance = budget
    
    # B. Prop Firm (SuperFunded)
    prop_data = []
    # 失敗回数分のコスト + 合格時のコスト
    total_cost = prop_fee * (1 + failures)
    prop_balance = -total_cost # スタートはマイナス（投資コスト）
    
    # 評価期間の遅延 (1回失敗につき1ヶ月 + 合格時2ヶ月の無給期間と仮定)
    months_delayed = failures + 2
    
    # 12ヶ月シミュレーション
    for m in range(1, 13):
        # CFD: 複利で増えると仮定 (うまくいった場合)
        p_profit = personal_balance * (monthly_roi / 100)
        personal_balance += p_profit
        personal_data.append(personal_balance - budget) # 純利益

        # Prop: 遅延後は巨額運用
        if m <= months_delayed:
            prop_data.append(prop_balance) # 変わらず
        else:
            # 利益分配 (80%)
            gross_profit = prop_acc_size * (monthly_roi / 100)
            payout = gross_profit * 0.8
            prop_balance += payout
            prop_data.append(prop_balance)
            
    return personal_data, prop_data, months_delayed, total_cost

# --- 3. Main UI ---

st.title("⚡ THE SMART SWITCH: CFD vs PROP")
st.markdown("<h4 style='color:#aaa;'>HIGH LEVERAGE REALITY CHECK</h4>", unsafe_allow_html=True)

# サイドバー設定
with st.sidebar:
    st.header("📊 YOUR PARAMETERS")
    
    budget = st.number_input("Trading Budget ($)", value=500, step=100, help="失っても生活に支障がない資金")
    monthly_roi = st.slider("Monthly ROI (%)", 1.0, 20.0, 5.0, 0.5, help="安定して出せる月利")
    
    st.markdown("---")
    st.header("🏆 PROP CHALLENGE")
    
    # 口座サイズ
    acc_map = {5000: 49, 10000: 99, 25000: 199, 50000: 299, 100000: 499}
    selected_size = st.selectbox("Target Account ($)", list(acc_map.keys()), index=2, format_func=lambda x: f"${x:,}")
    fee = acc_map[selected_size]
    
    st.markdown(f"**Fee: ${fee}**")
    
    # ハードル
    failures = st.slider("Expected Failures", 0, 5, 2, help="合格するまでに何回失敗しそうですか？")
    
    st.markdown("---")
    st.info("💡 Comparison: Trading your own cash vs Buying a challenge.")

# --- SECTION 1: 期待値シミュレーター (The Reality of Flipping) ---

st.subheader("🎲 The Gambler's Dilemma (Risk Calculator)")
st.markdown("海外FXで「少額を10倍にする」のと、プロップで「評価を通過する」の期待値を比較します。")

# 入力ゲージ
c_g1, c_g2 = st.columns(2)
with c_g1:
    target_x = st.slider("Target Multiplier (Profit Goal)", 2.0, 10.0, 5.0, 0.5, format="x%.1f")
    st.caption(f"Goal: Turn ${budget} into ${budget*target_x:,.0f} (x{target_x})")
    
with c_g2:
    success_rate = st.slider("Probability of Success (%)", 1, 20, 5, 1)
    st.caption(f"Chance of achieving x{target_x} without blowing up: {success_rate}%")

# 期待値計算
# CFD: 成功なら目標額ゲット、失敗なら全損
ev_cfd = (budget * target_x * (success_rate/100)) - (budget * (1 - success_rate/100))

# Prop: 成功なら口座ゲット(価値は月利x12ヶ月分と仮定)、失敗なら手数料損
# 口座の推定価値 = (AccountSize * 5% * 80% split) * 12 months (年収ベース)
prop_value = (selected_size * 0.05 * 0.8) * 12 
ev_prop = (prop_value * (success_rate/100)) - (fee * (1 - success_rate/100))

# ゲージ表示
k1, k2, k3 = st.columns(3)

with k1:
    st.markdown(f"""
    <div class="glass-card loser-card">
        <div class="kpi-label">CFD EXPECTED VALUE</div>
        <div class="kpi-value" style="color: {'#ff0055' if ev_cfd < 0 else '#fff'};">${ev_cfd:,.0f}</div>
        <div class="kpi-sub">High Risk of Ruin</div>
    </div>""", unsafe_allow_html=True)

with k2:
    st.markdown(f"""
    <div class="glass-card" style="border:none; background:transparent; box-shadow:none;">
        <div style="font-size:1rem; color:#888;">THE VERDICT</div>
        <div style="font-size:1.2rem; color:#ccc;">Same {success_rate}% Win Rate</div>
        <div style="font-size:3rem; font-weight:900; color:#00ff99;">PROFITABLE</div>
    </div>""", unsafe_allow_html=True)

with k3:
    st.markdown(f"""
    <div class="glass-card winner-card">
        <div class="kpi-label">PROP EXPECTED VALUE</div>
        <div class="kpi-value" style="color: #00ff99;">${ev_prop:,.0f}</div>
        <div class="kpi-sub">Risk is Capped at Fee</div>
    </div>""", unsafe_allow_html=True)

st.markdown(f"""
<div class="danger-zone">
    <b>📉 REALITY CHECK:</b><br>
    Trying to flip <b>${budget} to ${budget*target_x:,.0f}</b> in CFD usually has a negative expected value (you lose money over time).<br>
    With the same <b>{success_rate}% success rate</b>, passing a Prop Challenge creates an asset worth <b>${prop_value:,.0f}/year</b>.<br>
    The math is simple: <b>Don't gamble your principal. Risk our capital.</b>
</div>
""", unsafe_allow_html=True)

# --- SECTION 2: 12-Month Trajectory ---

st.markdown("---")
st.subheader("📈 1-Year Financial Projection")

# シミュレーション実行
cfd_res, prop_res, delay, cost = run_simulation(budget, monthly_roi, failures, selected_size, fee)
df = pd.DataFrame({"Month": range(1, 13), "CFD": cfd_res, "Prop": prop_res})

# 最終結果
final_cfd = cfd_res[-1]
final_prop = prop_res[-1]
multiplier = final_prop / final_cfd if final_cfd > 0 else 0

# グラフ描画
fig = go.Figure()

# CFD Line
fig.add_trace(go.Scatter(
    x=df['Month'], y=df['CFD'],
    mode='lines+markers', name=f'CFD (Start ${budget})',
    line=dict(color='#ff0055', width=2, dash='dash')
))

# Prop Line
fig.add_trace(go.Scatter(
    x=df['Month'], y=df['Prop'],
    mode='lines+markers', name=f'SuperFunded ${selected_size:,}',
    line=dict(color='#00ff99', width=4)
))

# 評価期間のアノテーション
if delay < 12:
    fig.add_vrect(
        x0=0, x1=delay,
        fillcolor="grey", opacity=0.1,
        layer="below", line_width=0,
        annotation_text=f"EVALUATION & FAILURES ({failures}x)", 
        annotation_position="top left", annotation_font_color="#aaa"
    )

fig.update_layout(
    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    font_color='#ccc', height=450,
    xaxis=dict(showgrid=False, title="Month"),
    yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.1)', title="Net Profit ($)"),
    legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center")
)
st.plotly_chart(fig, use_container_width=True)

# 結論メッセージ
st.markdown(f"""
<div style="text-align:center; padding:20px;">
    <h2>Total Difference: <span style="color:#00ff99">${final_prop - final_cfd:,.0f}</span></h2>
    <p style="color:#aaa;">
        Even if you fail <b>{failures} times</b>, the Prop model beats compounding your own cash.<br>
        Stop playing small. Start trading big.
    </p>
</div>
""", unsafe_allow_html=True)

if st.button("🔥 START YOUR CHALLENGE (Risk: Fees Only) 🔥"):
    st.balloons()