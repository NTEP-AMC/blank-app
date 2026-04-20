import streamlit as st
import pandas as pd
import base64

st.set_page_config(page_title="AMC NTEP Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 1rem; max-width: 1000px; }
    .amc-footer { text-align: center; font-size: 11px; color: #555; margin-top: 10px; padding-top: 10px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center; color: #1f618d; margin-top: 50px;'>🏥 AMC NTEP Login</h2>", unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if pwd == "AMC@2026": st.session_state.auth = True; st.rerun()
        else: st.error("Wrong Password")
    st.stop()

def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

def draw_card(title, value, color, icon):
    return f"""
    <div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="font-size: 24px; margin-bottom: 5px;">{icon}</div>
        <div style="font-size: 13px; font-weight: bold; text-transform: uppercase; line-height: 1.1;">{title}</div>
        <div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div>
    </div>
    """

# --- LOAD DATA ---
try:
    df_master = pd.read_csv("Master_Line_List.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_master.columns: df_master[col] = pd.to_datetime(df_master[col], errors='coerce')
    df_comp = pd.read_csv("Comparison_Matrix.csv")
except:
    st.error("⚠️ ડેટા અપડેટ કરો...")
    st.stop()

# --- HEADER ---
b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")
b64_h1, b64_h2 = img_to_b64("images/h1.jpg"), img_to_b64("images/h2.jpg")

st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)
st.markdown(f"<div style='display:flex; gap:8px; margin-bottom: 20px;'><img src='data:image/jpeg;base64,{b64_h1}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'><img src='data:image/jpeg;base64,{b64_h2}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'></div>", unsafe_allow_html=True)

# --- TABS ---
tab1, tab2 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison"])

with tab1:
    with st.expander("🔽 Filters & Sorting"):
        inds = ["SLPA", "UDST", "Not Put On", "Outcome", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
        f_rep = st.multiselect("Report Type", inds)
        
        c1, c2 = st.columns(2)
        with c1:
            z_opts = sorted([str(x) for x in df_master['ZONE'].unique() if str(x) not in ["nan", "", "None", "N/A"]])
            s_z = st.multiselect("Zone", z_opts)
            
            df_tu = df_master[df_master['ZONE'].isin(s_z)] if s_z else df_master
            tu_opts = sorted([str(x) for x in df_tu['TB Unit'].unique() if str(x) not in ["nan", "", "None", "N/A"]])
            s_tu = st.multiselect("TB Unit", tu_opts)
        with c2:
            df_phi = df_tu[df_tu['TB Unit'].isin(s_tu)] if s_tu else df_tu
            phi_opts = sorted([str(x) for x in df_phi['PHI'].unique() if str(x) not in ["nan", "", "None", "N/A"]])
            s_phi = st.multiselect("PHI", phi_opts)
            
            df_ft = df_phi[df_phi['PHI'].isin(s_phi)] if s_phi else df_phi
            ft_opts = sorted([str(x) for x in df_ft['Facility Type'].unique() if str(x) not in ["nan", "", "None", "N/A"]])
            s_ft = st.multiselect("Facility Type", ft_opts)

        d1, d2, d3 = st.columns(3)
        with d1: dr_diag = st.date_input("Diagnosis Date", value=[])
        if st.button("Reset Filters", key="r1"): st.rerun()

    df_disp = df_master.copy()
    if s_z: df_disp = df_disp[df_disp['ZONE'].isin(s_z)]
    if s_tu: df_disp = df_disp[df_disp['TB Unit'].isin(s_tu)]
    if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
    if s_ft: df_disp = df_disp[df_disp['Facility Type'].isin(s_ft)]
    if f_rep: df_disp = df_disp[df_disp['Pending Status'].str.contains("|".join(f_rep), na=False)]

    if len(dr_diag) == 2:
        df_disp = df_disp[(df_disp['Diagnosis Date'].dt.date >= dr_diag[0]) & (df_disp['Diagnosis Date'].dt.date <= dr_diag[1])]

    f_counts = {k: len(df_disp[df_disp['Pending Status'].str.contains(k, na=False)]) for k in inds}
    
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(draw_card("Total Pending", len(df_disp), "#1f618d", "👥"), unsafe_allow_html=True)
    with c2: st.markdown(draw_card("Outcome Pending", f_counts["Outcome"], "#F39C12", "🏥"), unsafe_allow_html=True)
    with c3: st.markdown(draw_card("UDST Pending", f_counts["UDST"], "#C0392B", "🧪"), unsafe_allow_html=True)
    with c4: st.markdown(draw_card("Not Put On", f_counts["Not Put On"], "#27AE60", "⏳"), unsafe_allow_html=True)

    with st.expander("View All Other Pending Indicators"):
        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1: st.markdown(draw_card("SLPA", f_counts["SLPA"], "#D35400", "🔬"), unsafe_allow_html=True)
        with r2_c2: st.markdown(draw_card("Consent", f_counts["Consent"], "#8E44AD", "📝"), unsafe_allow_html=True)
        with r2_c3: st.markdown(draw_card("ADT", f_counts["ADT"], "#16A085", "🩸"), unsafe_allow_html=True)
        with r2_c4: st.markdown(draw_card("RBS", f_counts["RBS"], "#E67E22", "💉"), unsafe_allow_html=True)
        r3_c1, r3_c2, r3_c3, r3_c4 = st.columns(4)
        with r3_c1: st.markdown(draw_card("ART", f_counts["ART"], "#2980B9", "💊"), unsafe_allow_html=True)
        with r3_c2: st.markdown(draw_card("CPT", f_counts["CPT"], "#D35400", "🛡️"), unsafe_allow_html=True)
        with r3_c3: st.markdown(draw_card("HIV", f_counts["HIV"], "#C0392B", "🩺"), unsafe_allow_html=True)

    st.dataframe(df_disp, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("#### 🔄 Comparison Matrix")
    with st.expander("🔽 Dependent Filters"):
        c1, c2 = st.columns(2)
        with c1:
            z2_opts = sorted([str(x) for x in df_comp['ZONE'].unique() if str(x) not in ["nan", "", "None", "N/A"]])
            s2_z = st.multiselect("Filter Zone", z2_opts, key='z2')
            
            df2_tu = df_comp[df_comp['ZONE'].isin(s2_z)] if s2_z else df_comp
            tu2_opts = sorted([str(x) for x in df2_tu['TB Unit'].unique() if str(x) not in ["nan", "", "None", "N/A"]])
            s2_tu = st.multiselect("Filter TB Unit", tu2_opts, key='tu2')
        with c2:
            df2_phi = df2_tu[df2_tu['TB Unit'].isin(s2_tu)] if s2_tu else df2_tu
            phi2_opts = sorted([str(x) for x in df2_phi['PHI'].unique() if str(x) not in ["nan", "", "None", "N/A"]])
            s2_phi = st.multiselect("Filter PHI", phi2_opts, key='phi2')
            
    df_c_disp = df_comp.copy()
    if s2_z: df_c_disp = df_c_disp[df_c_disp['ZONE'].isin(s2_z)]
    if s2_tu: df_c_disp = df_c_disp[df_c_disp['TB Unit'].isin(s2_tu)]
    if s2_phi: df_c_disp = df_c_disp[df_c_disp['PHI'].isin(s2_phi)]

    t_new = (df_c_disp == "🔴 NEW").sum().sum()
    t_res = (df_c_disp == "🟢 RESOLVED").sum().sum()
    t_per = (df_c_disp == "🟡 PERSISTENT").sum().sum()
    t_total = t_new + t_per
    
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.markdown(draw_card("Total Active", t_total, "#1f618d", "📊"), unsafe_allow_html=True)
    with k2: st.markdown(draw_card("New Pendency", t_new, "#C0392B", "🔴"), unsafe_allow_html=True)
    with k3: st.markdown(draw_card("Resolved", t_res, "#27AE60", "🟢"), unsafe_allow_html=True)
    with k4: st.markdown(draw_card("Persistent", t_per, "#F39C12", "🟡"), unsafe_allow_html=True)
    
    st.dataframe(df_c_disp, use_container_width=True, hide_index=True)

# --- FOOTER & SMALL TIMESTAMPS AT THE BOTTOM ---
try:
    df_times = pd.read_csv("Update_Timestamps.csv")
    time_html = "<div style='display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin-top:20px; padding-top:15px; border-top:1px solid #ddd;'>"
    for _, r in df_times.iterrows():
        color = "#27AE60" if r['Last Updated'] != "N/A" else "#C0392B"
        time_html += f"<div style='background:#f4f6f7; padding:4px 8px; border-radius:4px; text-align:center; border-left:3px solid {color}; box-shadow: 0 1px 2px rgba(0,0,0,0.05);'><div style='font-size:9px; color:#666; text-transform:uppercase;'><b>{r['Register']}</b></div><div style='font-size:10px; color:#222; margin-top:1px;'>🕒 {r['Last Updated']}</div></div>"
    time_html += "</div>"
    st.markdown(time_html, unsafe_allow_html=True)
except:
    pass

st.markdown("<div class='amc-footer'>Created by District TB Center AMC | NTEP Monitoring System</div>", unsafe_allow_html=True)
