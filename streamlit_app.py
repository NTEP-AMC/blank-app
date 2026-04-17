import streamlit as st
import pandas as pd
import glob
import os
import base64
import json
import io
from datetime import datetime

# --- GOOGLE DRIVE TOOLS ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="AMC NTEP Master Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1rem; max-width: 1150px; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #1f618d !important; color: white !important; }
    .report-mini-box { background-color: #eaf2f8; border-left: 5px solid #1f618d; padding: 8px 15px; border-radius: 5px; margin: 5px; text-align: center; display: inline-block; min-width: 120px; font-size: 14px; font-weight: bold; color: #1f618d; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center; color: #1f618d; margin-top: 50px;'>🏥 AMC NTEP Secure Login</h2>", unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Access Dashboard", use_container_width=True):
        if pwd == "AMC@2026": st.session_state.auth = True; st.rerun()
        else: st.error("Incorrect Password")
    st.stop()

# --- HEADER ---
def img_to_b64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return ""

src_amc = f"data:image/png;base64,{img_to_b64('images/amc.png')}"
src_ntep = f"data:image/jpeg;base64,{img_to_b64('images/ntep.jpg')}"

st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center;'>
    <img src='{src_amc}' height='60'>
    <h3 style='margin:0; color:#333; font-weight:900;'>AMC <span style='color:#ccc;'>|</span> NTEP</h3>
    <img src='{src_ntep}' height='60'>
</div>
<div style='background-color: #1f618d; color: white; text-align: center; padding: 8px; font-weight: bold; border-radius: 5px; margin: 10px 0;'>
   TB Monitoring Dashboard - Ahmedabad
</div>
""", unsafe_allow_html=True)

# --- HELPERS ---
def cx(letter):
    num = 0
    for c in letter.upper(): num = num * 26 + (ord(c) - ord('A') + 1)
    return num - 1

def draw_card(title, value, color, icon):
    return f"""
    <div style="background-color: {color}; border-radius: 8px; padding: 20px; color: white; text-align: center; margin-bottom: 15px;">
        <div style="font-size: 24px;">{icon}</div>
        <div style="font-size: 12px; font-weight: bold; text-transform: uppercase;">{title}</div>
        <div style="font-size: 32px; font-weight: 900; margin-top: 5px;">{value}</div>
    </div>
    """

# --- ZONE MAPPING (FIXED TYPO HERE) ---
df_zone = pd.DataFrame()
try:
    if os.path.exists("data/zone_mapping.xlsx"):
        df_zone = pd.read_excel("data/zone_mapping.xlsx", usecols=[0, 1])
        df_zone.columns = ['PHI_Map', 'ZONE']
except: pass

tab1, tab2 = st.tabs(["📊 Master Dashboard", "🔄 Comparison Tracker"])

# ==========================================
# TAB 1: MASTER
# ==========================================
with tab1:
    files = glob.glob("data/*.xlsx")
    all_data = []
    # Using your specific report names
    counts = {"Lab Pending": 0, "Notification": 0, "Co-morbidity": 0, "PMTBMBA": 0}

    for f in files:
        if "~$" in f or "zone" in f.lower(): continue
        df = pd.read_excel(f)
        
        # MAPPING AS PER YOUR IMAGE
        if len(df.columns) > 19 and 'episode' in str(df.columns[cx('T')]).lower():
            temp = pd.DataFrame({
                'PHI': df.iloc[:, cx('Q')], 'TB UNIT': df.iloc[:, cx('P')], 'EPISODE ID': df.iloc[:, cx('T')],
                'PATIENT NAME': df.iloc[:, cx('V')], 'DIAGNOSIS DATE': df.iloc[:, cx('A')],
                'TREATMENT OUTCOME': df.iloc[:, cx('AE')], 'REPORT PENDING TYPE': "Lab Pending"
            })
            counts["Lab Pending"] += len(temp)
        elif len(df.columns) > 12 and 'episode' in str(df.columns[cx('M')]).lower():
            temp = pd.DataFrame({
                'PHI': df.iloc[:, cx('E')], 'TB UNIT': df.iloc[:, cx('C')], 'EPISODE ID': df.iloc[:, cx('M')],
                'PATIENT NAME': df.iloc[:, cx('N')], 'DIAGNOSIS DATE': df.iloc[:, cx('S')],
                'TREATMENT OUTCOME': df.iloc[:, cx('BK')], 'REPORT PENDING TYPE': "Notification"
            })
            counts["Notification"] += len(temp)
        elif len(df.columns) > 10 and 'episode' in str(df.columns[cx('K')]).lower():
            temp = pd.DataFrame({
                'PHI': df.iloc[:, cx('D')], 'TB UNIT': df.iloc[:, cx('C')], 'EPISODE ID': df.iloc[:, cx('K')],
                'PATIENT NAME': df.iloc[:, cx('O')], 'DIAGNOSIS DATE': df.iloc[:, cx('M')],
                'TREATMENT OUTCOME': df.iloc[:, cx('U')], 'REPORT PENDING TYPE': "Co-morbidity"
            })
            counts["Co-morbidity"] += len(temp)
        else: continue
        all_data.append(temp)

    if all_data:
        df_m = pd.concat(all_data).drop_duplicates()
        if not df_zone.empty:
            df_m = df_m.merge(df_zone, left_on='PHI', right_on='PHI_Map', how='left').drop(columns=['PHI_Map'])
            df_m['ZONE'] = df_m['ZONE'].fillna("Unknown")
        else: df_m['ZONE'] = "No Zone Map"

        c1, c2 = st.columns(2)
        with c1: st.markdown(draw_card("Unique Patients", len(df_m['EPISODE ID'].unique()), "#1f618d", "👥"), unsafe_allow_html=True)
        with c2: st.markdown(draw_card("Total Pendency", len(df_m), "#d35400", "📋"), unsafe_allow_html=True)

        # MINI BOXES (HIV: 10 style)
        html_boxes = "".join([f"<div class='report-mini-box'>{k}: {v}</div>" for k, v in counts.items() if v > 0])
        st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'>{html_boxes}</div>", unsafe_allow_html=True)

        st.write("### Patient Master Line List")
        cols = ['ZONE', 'TB UNIT', 'PHI', 'EPISODE ID', 'PATIENT NAME', 'DIAGNOSIS DATE', 'TREATMENT OUTCOME', 'REPORT PENDING TYPE']
        st.dataframe(df_m[cols], use_container_width=True, hide_index=True)

# ==========================================
# TAB 2: COMPARISON (SMART LATEST ONLY)
# ==========================================
with tab2:
    if st.button("🔄 Check Latest Drive Upload & Compare", use_container_width=True):
        try:
            creds_info = json.loads(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
            service = build('drive', 'v3', credentials=creds)
            
            res = service.files().list(q="name='AMC_NTEP_Data' and mimeType='application/vnd.google-apps.folder'", fields="files(id)").execute()
            p_id = res.get('files', [{}])[0].get('id')
            subs = service.files().list(q=f"'{p_id}' in parents", fields="files(id, name)", orderBy="name").execute().get('files', [])
            
            if len(subs) >= 2:
                old_f, new_f = subs[-2], subs[-1]
                
                def get_data(f_id):
                    items = service.files().list(q=f"'{f_id}' in parents and name contains '.xlsx'", fields="files(id, name)").execute().get('files', [])
                    rows = []
                    for it in items:
                        req = service.files().get_media(fileId=it['id'])
                        fh = io.BytesIO(); MediaIoBaseDownload(fh, req).next_chunk(); fh.seek(0)
                        df = pd.read_excel(fh)
                        for _, r in df.iterrows():
                            if len(df.columns) > 19: id_c, nm_c, ph_c, tu_c, dg_c, ot_c = 'T', 'V', 'Q', 'P', 'A', 'AE'
                            elif len(df.columns) > 12: id_c, nm_c, ph_c, tu_c, dg_c, ot_c = 'M', 'N', 'E', 'C', 'S', 'BK'
                            else: id_c, nm_c, ph_c, tu_c, dg_c, ot_c = 'K', 'O', 'D', 'C', 'M', 'U'
                            rows.append({'EPISODE ID': str(r.iloc[cx(id_c)]), 'PATIENT NAME': r.iloc[cx(nm_c)], 'PHI': r.iloc[cx(ph_c)], 'TU': r.iloc[cx(tu_c)], 'OUTCOME': r.iloc[cx(ot_c)], 'Register': it['name']})
                    return pd.DataFrame(rows).drop_duplicates(subset=['EPISODE ID'])

                with st.spinner("Comparing files..."):
                    df_old = get_data(old_f['id'])
                    df_new = get_data(new_f['id'])
                    
                    # Logic: Only show the registers that exist in the latest folder
                    latest_registers = df_new['Register'].unique()
                    df_old_filtered = df_old[df_old['Register'].isin(latest_registers)]
                    
                    persistent = df_new[df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
                    persistent['Status'] = "🔴 Persistent"
                    new_pat = df_new[~df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
                    new_pat['Status'] = "🔵 New Entry"
                    resolved = df_old_filtered[~df_old_filtered['EPISODE ID'].isin(df_new['EPISODE ID'])].copy()
                    resolved['Status'] = "🟢 Resolved"

                    st.info(f"📍 Latest Register identified: **{', '.join(latest_registers)}** (from {new_f['name']})")
                    
                    res_final = pd.concat([persistent, new_pat, resolved])
                    st.dataframe(res_final[['Status', 'PATIENT NAME', 'EPISODE ID', 'PHI', 'TU', 'OUTCOME', 'Register']], use_container_width=True, hide_index=True)
            else: st.error("Need 2 folders in Drive (Old vs New).")
        except Exception as e: st.error(f"Error: {e}")

st.markdown("<div style='text-align: center; font-size: 11px; margin-top: 30px; color: #888;'>District TB Center AMC | Monitoring Portal v4.1</div>", unsafe_allow_html=True)
