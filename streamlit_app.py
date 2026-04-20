import streamlit as st
import pandas as pd
import base64

st.set_page_config(page_title="AMC NTEP Dashboard", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
<style>
    #MainMenu {visibility: hidden;} header {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1000px; }
    .amc-footer { text-align: center; font-size: 11px; color: #555; margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-weight: bold; }
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

# --- LOAD COLAB DATA ---
try:
    df_master = pd.read_csv("Master_Line_List.csv")
    for col in ['Diagnosis Date', 'Initiation Date', 'Outcome Date']:
        if col in df_master.columns: df_master[col] = pd.to_datetime(df_master[col], errors='coerce')
    
    df_comp = pd.read_csv("Comparison_Matrix.csv")
    for c in ['ZONE', 'PHI', 'TB Unit', 'Episode ID', 'Patient Name']:
        if c not in df_comp.columns: df_comp[c] = ""
except:
    st.error("⚠️ ડેટા હજુ અપડેટ નથી થયો. કૃપા કરીને Google Colab માં Play બટન દબાવો.")
    st.stop()

# --- HEADER ---
b64_amc, b64_ntep = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg")
b64_h1, b64_h2 = img_to_b64("images/h1.jpg"), img_to_b64("images/h2.jpg")

st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='data:image/png;base64,{b64_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='data:image/jpeg;base64,{b64_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)
st.markdown(f"<div style='display:flex; gap:8px; margin-bottom: 20px;'><img src='data:image/jpeg;base64,{b64_h1}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'><img src='data:image/jpeg;base64,{b64_h2}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'></div>", unsafe_allow_html=True)

# --- TABS ---
tab1, tab2 = st.tabs(["📊 Master Dashboard (Tab 1)", "🔄 Daily Comparison (Tab 2)"])

with tab1:
    with st.expander("🔽 Filters & Sorting"):
        indicators = ["SLPA", "UDST", "Not Put On", "Outcome", "Consent", "ADT", "RBS", "ART", "CPT", "HIV"]
        f_rep = st.multiselect("Report Type", indicators, placeholder="All Reports")
        
        c1, c2 = st.columns(2)
        with c1:
            s_z = st.multiselect("Zone", sorted([str(x) for x in df_master['ZONE'].unique() if str(x) not in ["nan", "", "None"]]))
            tu_opts = sorted([str(x) for x in df_master[df_master['ZONE'].isin(s_z)]['TB Unit'].unique() if str(x) not in ["nan", "", "None"]]) if s_z else sorted([str(x) for x in df_master['TB Unit'].unique() if str(x) not in ["nan", "", "None"]])
            s_tu = st.multiselect("TB Unit", tu_opts)
        with c2:
            s_ft = st.multiselect("Facility Type", sorted([str(x) for x in df_master['Facility Type'].unique() if str(x) not in ["nan", "", "None"]]))
            s_phi = st.multiselect("PHI", sorted([str(x) for x in df_master['PHI'].unique() if str(x) not in ["nan", "", "None"]]))
        
        st.markdown("---")
        d1, d2, d3 = st.columns(3)
        with d1: dr_diag = st.date_input("Diagnosis Date Filter", value=[], key="dr1")
        with d2: dr_init = st.date_input("Initiation Date Filter", value=[], key="dr2")
        with d3: dr_out = st.date_input("Outcome Date Filter", value=[], key="dr3")
        if st.button("Reset Filters", use_container_width=True): st.rerun()

    df_disp = df_master.copy()
    if s_z: df_disp = df_disp[df_disp['ZONE'].isin(s_z)]
    if s_tu: df_disp = df_disp[df_disp['TB Unit'].isin(s_tu)]
    if s_ft: df_disp = df_disp[df_disp['Facility Type'].isin(s_ft)]
    if s_phi: df_disp = df_disp[df_disp['PHI'].isin(s_phi)]
    if f_rep: df_disp = df_disp[df_disp['Pending Status'].str.contains("|".join(f_rep), na=False)]

    for col, dr in [('Diagnosis Date', dr_diag), ('Initiation Date', dr_init), ('Outcome Date', dr_out)]:
        if len(dr) == 2:
            df_disp = df_disp[(df_disp[col].dt.date >= dr[0]) & (df_disp[col].dt.date <= dr[1])]

    f_counts = {k: len(df_disp[df_disp['Pending Status'].str.contains(k, na=False)]) for k in indicators}

    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(draw_card("Total Pending Patients", len(df_disp), "#1f618d", "👥"), unsafe_allow_html=True)
    with c2: st.markdown(draw_card("Not Put On", f_counts["Not Put On"], "#27AE60", "⏳"), unsafe_allow_html=True)
    with c3: st.markdown(draw_card("Outcome Pending", f_counts["Outcome"], "#F39C12", "🏥"), unsafe_allow_html=True)
    with c4: st.markdown(draw_card("UDST Pending", f_counts["UDST"], "#C0392B", "🧪"), unsafe_allow_html=True)

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

    st.markdown("#### Patient Line List")
    sq = st.text_input("🔍 Search Name or ID", "")
    if sq: df_disp = df_disp[df_disp['Patient Name'].str.contains(sq, case=False, na=False) | df_disp['Episode ID'].astype(str).str.contains(sq, case=False, na=False)]

    conf = {"Diagnosis Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Initiation Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Outcome Date": st.column_config.DateColumn(format="DD-MM-YYYY")}
    st.dataframe(df_disp, use_container_width=True, hide_index=True, column_config=conf, height=400)
    st.download_button("📥 Download Master Data (CSV)", df_disp.to_csv(index=False).encode('utf-8'), "NTEP_Master_Data.csv", "text/csv", use_container_width=True)

with tab2:
    st.markdown("#### 🔄 પ્રગતિ રિપોર્ટ: NEW vs PERSISTENT vs RESOLVED")
    
    # --- 3 KPI બોક્સ ---
    total_new = (df_comp == "🔴 NEW").sum().sum()
    total_res = (df_comp == "🟢 RESOLVED").sum().sum()
    total_per = (df_comp == "🟡 PERSISTENT").sum().sum()
    
    k1, k2, k3 = st.columns(3)
    with k1: st.markdown(draw_card("New Pendency", total_new, "#C0392B", "🔴"), unsafe_allow_html=True)
    with k2: st.markdown(draw_card("Resolved Work", total_res, "#27AE60", "🟢"), unsafe_allow_html=True)
    with k3: st.markdown(draw_card("Still Pending", total_per, "#F39C12", "🟡"), unsafe_allow_html=True)

    # --- ફિલ્ટર્સ ---
    with st.expander("🔽 Filters for Comparison"):
        c1, c2 = st.columns(2)
        with c1:
            s2_z = st.multiselect("Filter Zone", sorted([str(x) for x in df_comp['ZONE'].unique() if str(x) not in ["nan", "", "None"]]), key='z2')
            tu2_opts = sorted([str(x) for x in df_comp[df_comp['ZONE'].isin(s2_z)]['TB Unit'].unique() if str(x) not in ["nan", "", "None"]]) if s2_z else sorted([str(x) for x in df_comp['TB Unit'].unique() if str(x) not in ["nan", "", "None"]])
            s2_tu = st.multiselect("Filter TB Unit", tu2_opts, key='tu2')
        with c2:
            s2_phi = st.multiselect("Filter PHI", sorted([str(x) for x in df_comp['PHI'].unique() if str(x) not in ["nan", "", "None"]]), key='phi2')
            
    df_comp_disp = df_comp.copy()
    if s2_z: df_comp_disp = df_comp_disp[df_comp_disp['ZONE'].isin(s2_z)]
    if s2_tu: df_comp_disp = df_comp_disp[df_comp_disp['TB Unit'].isin(s2_tu)]
    if s2_phi: df_comp_disp = df_comp_disp[df_comp_disp['PHI'].isin(s2_phi)]

    st.markdown("---")
    sq2 = st.text_input("🔍 Search Name or ID in Comparison", "", key='sq2')
    if sq2: df_comp_disp = df_comp_disp[df_comp_disp['Patient Name'].str.contains(sq2, case=False, na=False) | df_comp_disp['Episode ID'].astype(str).str.contains(sq2, case=False, na=False)]
    
    st.dataframe(df_comp_disp, use_container_width=True, hide_index=True, height=500)
    st.download_button("📥 Download Comparison (CSV)", df_comp_disp.to_csv(index=False).encode('utf-8'), "NTEP_Comparison.csv", "text/csv", use_container_width=True)

st.markdown("<div class='amc-footer'>Created by District TB Center AMC | NTEP Auto-Dashboard Framework</div>", unsafe_allow_html=True)
