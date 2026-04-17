import streamlit as st
import pandas as pd
import glob
import os
import base64

st.set_page_config(page_title="AMC NTEP Master Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1100px; }
    .amc-footer { text-align: center; font-size: 11px; color: #555; margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px 5px 0 0; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #1f618d !important; color: white !important; }
    .login-box { border: 1px solid #ddd; padding: 30px; border-radius: 10px; background-color: #f9f9f9; text-align: center; margin-top: 50px; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN SCREEN ---
if "auth" not in st.session_state: st.session_state.auth = False

if not st.session_state.auth:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div class='login-box'>", unsafe_allow_html=True)
        st.markdown("<h2 style='color: #1f618d;'>🏥 AMC NTEP Login</h2>", unsafe_allow_html=True)
        pwd = st.text_input("Enter Dashboard Password", type="password")
        if st.button("Login", use_container_width=True):
            if pwd == "AMC@2026": 
                st.session_state.auth = True
                st.rerun()
            else: 
                st.error("Incorrect Password")
        st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- HEADER & IMAGES ---
def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

src_amc = f"data:image/png;base64,{img_to_b64('images/amc.png')}"
src_ntep = f"data:image/jpeg;base64,{img_to_b64('images/ntep.jpg')}"
src_h1 = f"data:image/jpeg;base64,{img_to_b64('images/h1.jpg')}"
src_h2 = f"data:image/jpeg;base64,{img_to_b64('images/h2.jpg')}"

st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; padding: 0 10px;'>
    <img src='{src_amc}' height='70'>
    <h3 style='margin:0; color:#333; font-weight:900;'>AMC <span style='color:#ccc;'>|</span> NTEP</h3>
    <img src='{src_ntep}' height='70'>
</div>
<div style='background-color: #1f618d; color: white; text-align: center; padding: 10px; font-weight: bold; border-radius: 5px; margin: 15px 0;'>
   TB Monitoring Dashboard - Ahmedabad
</div>
<div style='display: flex; gap: 8px; margin-bottom: 20px;'>
    <img src='{src_h1}' style='width: 50%; height: 120px; object-fit: cover; border-radius: 5px;'>
    <img src='{src_h2}' style='width: 50%; height: 120px; object-fit: cover; border-radius: 5px;'>
</div>
""", unsafe_allow_html=True)

# --- HELPERS ---
def cx(col_letter):
    num = 0
    for c in col_letter.upper(): num = num * 26 + (ord(c) - ord('A') + 1)
    return num - 1

def draw_card(title, value, color, icon):
    return f"""
    <div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="font-size: 20px;">{icon}</div>
        <div style="font-size: 11px; font-weight: bold; text-transform: uppercase;">{title}</div>
        <div style="font-size: 28px; font-weight: 900; margin-top: 5px;">{value}</div>
    </div>
    """

tab1, tab2 = st.tabs(["📊 Master Dashboard (Local)", "🔄 Daily Comparison (Coming Soon)"])

# ==========================================
# TAB 1: MASTER DASHBOARD (OLD STABLE LOGIC)
# ==========================================
with tab1:
    files = glob.glob("data/*.xlsx")
    all_rows = []
    
    if not files:
        st.warning("No files found in the 'data/' folder. Please upload Excel registers to your GitHub repository.")
    else:
        for f in files:
            if "~$" in f or "zone" in f.lower(): continue
            try:
                df = pd.read_excel(f)
                report_name = os.path.basename(f)
                
                # Check column count to map correctly (Morning logic)
                if len(df.columns) > 19: # LAB
                    for _, r in df.iterrows():
                        all_rows.append({'Episode ID': str(r.iloc[cx('T')]), 'Patient Name': r.iloc[cx('V')], 'PHI': r.iloc[cx('Q')], 'TB Unit': r.iloc[cx('P')], 'Report Type': 'Lab Pending'})
                elif len(df.columns) > 12: # NOTIFICATION
                    for _, r in df.iterrows():
                        all_rows.append({'Episode ID': str(r.iloc[cx('M')]), 'Patient Name': r.iloc[cx('N')], 'PHI': r.iloc[cx('E')], 'TB Unit': r.iloc[cx('C')], 'Report Type': 'Notification'})
                elif len(df.columns) > 10: # COMORBIDITY
                    for _, r in df.iterrows():
                        all_rows.append({'Episode ID': str(r.iloc[cx('K')]), 'Patient Name': r.iloc[cx('O')], 'PHI': r.iloc[cx('D')], 'TB Unit': r.iloc[cx('C')], 'Report Type': 'Co-morbidity'})
            except:
                pass

        if all_rows:
            df_master = pd.DataFrame(all_rows).drop_duplicates(subset=['Episode ID'])
            
            # Top Cards
            c1, c2 = st.columns(2)
            with c1: st.markdown(draw_card("Total Unique Patients", len(df_master['Episode ID'].unique()), "#1f618d", "👥"), unsafe_allow_html=True)
            with c2: st.markdown(draw_card("Total Pendency", len(df_master), "#d35400", "📝"), unsafe_allow_html=True)

            # Filter Section
            st.write("### 🔎 Filters")
            f1, f2 = st.columns(2)
            sel_report = f1.multiselect("Filter by Report Type", df_master['Report Type'].unique())
            
            # Clean TB Unit list for filter
            tbu_list = [str(t) for t in df_master['TB Unit'].unique() if str(t).strip() and str(t) != 'nan']
            sel_tbu = f2.multiselect("Filter by TB Unit", sorted(tbu_list))
            
            # Apply filters
            filtered_df = df_master.copy()
            if sel_report: filtered_df = filtered_df[filtered_df['Report Type'].isin(sel_report)]
            if sel_tbu: filtered_df = filtered_df[filtered_df['TB Unit'].astype(str).isin(sel_tbu)]

            st.write("### Patient Line List")
            st.dataframe(filtered_df, use_container_width=True, hide_index=True)
            
            csv = filtered_df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download Filtered Data", data=csv, file_name="AMC_Pending_List.csv", mime='text/csv')

# ==========================================
# TAB 2: PLACEHOLDER
# ==========================================
with tab2:
    st.info("💡 Daily Comparison feature is currently under maintenance. Please use the Master Dashboard to view current pendency.")

st.markdown("<div class='amc-footer'>District TB Center Ahmedabad | AMC NTEP</div>", unsafe_allow_html=True)
