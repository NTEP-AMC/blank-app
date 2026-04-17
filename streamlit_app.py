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

st.set_page_config(page_title="VERIFICATION TEST 100", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 1000px; }
    .amc-footer { text-align: center; font-size: 11px; color: #555; margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #f0f2f6; border-radius: 5px; padding: 10px 20px; font-weight: bold; }
    .stTabs [aria-selected="true"] { background-color: #1f618d !important; color: white !important; }
    .status-box { background-color: #f8f9fa; border: 1px solid #dee2e6; padding: 10px; border-radius: 5px; text-align: center; margin-bottom: 15px; font-size: 13px; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center; color: #1f618d;'>🏥 AMC NTEP Login</h2>", unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if pwd == "AMC@2026": st.session_state.auth = True; st.rerun()
        else: st.error("Wrong Password")
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

# --- UTILITIES ---
def cx(letter):
    num = 0
    for c in letter.upper(): num = num * 26 + (ord(c) - ord('A') + 1)
    return num - 1

def draw_card(title, value, color, icon):
    return f"""
    <div style="background-color: {color}; border-radius: 8px; padding: 20px 10px; color: white; text-align: center;">
        <div style="font-size: 22px;">{icon}</div>
        <div style="font-size: 11px; font-weight: bold;">{title}</div>
        <div style="font-size: 28px; font-weight: 900; margin-top: 5px;">{value}</div>
    </div>
    """

tab1, tab2 = st.tabs(["📊 Master Dashboard", "🔄 Daily Comparison Tracker"])

# ==========================================
# TAB 1: MASTER DASHBOARD
# ==========================================
with tab1:
    files = glob.glob("data/*.xlsx")
    all_data = []
    report_stats = {}

    for f in files:
        if "~$" in f or "zone" in f.lower(): continue
        df = pd.read_excel(f)
        if df.empty: continue
        
        fname = os.path.basename(f)
        report_stats[fname] = len(df)
        
        # Mapping Logic based on your image
        col_t = str(df.columns[cx('T')]).lower() if len(df.columns) > 19 else "" # LAB
        col_m = str(df.columns[cx('M')]).lower() if len(df.columns) > 12 else "" # NOTIF
        col_k = str(df.columns[cx('K')]).lower() if len(df.columns) > 10 else "" # COMORB
        col_i = str(df.columns[cx('I')]).lower() if len(df.columns) > 8 else ""  # PMTBMBA

        if "episode" in col_t: # LAB
            temp = pd.DataFrame({
                'ID': df.iloc[:, cx('T')], 'Name': df.iloc[:, cx('V')], 
                'PHI': df.iloc[:, cx('Q')], 'TU': df.iloc[:, cx('P')],
                'Outcome': df.iloc[:, cx('AE')], 'Report': "Lab"
            })
        elif "episode" in col_m: # NOTIF
            temp = pd.DataFrame({
                'ID': df.iloc[:, cx('M')], 'Name': df.iloc[:, cx('N')], 
                'PHI': df.iloc[:, cx('E')], 'TU': df.iloc[:, cx('C')],
                'Outcome': df.iloc[:, cx('BK')], 'Report': "Notification"
            })
        elif "episode" in col_k: # COMORB
            temp = pd.DataFrame({
                'ID': df.iloc[:, cx('K')], 'Name': df.iloc[:, cx('O')], 
                'PHI': df.iloc[:, cx('D')], 'TU': df.iloc[:, cx('C')],
                'Outcome': df.iloc[:, cx('U')], 'Report': "Co-morbidity"
            })
        elif "episode" in col_i: # PMTBMBA / Consent
            temp = pd.DataFrame({
                'ID': df.iloc[:, cx('I')], 'Name': df.iloc[:, cx('J')], 
                'PHI': df.iloc[:, cx('W')], 'TU': df.iloc[:, cx('V')],
                'Outcome': "N/A", 'Report': "Consent"
            })
        else: continue
        all_data.append(temp)

    if all_data:
        df_master = pd.concat(all_data).drop_duplicates()
        df_master['Outcome'] = df_master['Outcome'].fillna("Pending").replace("nan", "Pending")
        
        st.markdown(f"<div class='status-box'>📍 Local Data Last Synced: {datetime.now().strftime('%d-%m-%Y %H:%M')}</div>", unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1: st.markdown(draw_card("Unique Patients", len(df_master['ID'].unique()), "#1f618d", "👤"), unsafe_allow_html=True)
        with c2: st.markdown(draw_card("Total Pendencies", len(df_master), "#d35400", "📋"), unsafe_allow_html=True)

        with st.expander("📂 Show Report Wise Breakdown"):
            for r_name, count in report_stats.items():
                st.write(f"**{r_name}:** {count}")

        st.write("### Patient Master List (With Outcomes)")
        st.dataframe(df_master[['ID', 'Name', 'Outcome', 'PHI', 'TU', 'Report']], use_container_width=True, hide_index=True)
        
        st.download_button("📥 Download List", df_master.to_csv(index=False), "AMC_NTEP_Master.csv", "text/csv", use_container_width=True)

# ==========================================
# TAB 2: DAILY COMPARISON
# ==========================================
with tab2:
    if st.button("🚀 Run Daily Comparison Tracking", use_container_width=True):
        try:
            creds_info = json.loads(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
            service = build('drive', 'v3', credentials=creds)
            
            res = service.files().list(q="name='AMC_NTEP_Data' and mimeType='application/vnd.google-apps.folder'", fields="files(id)").execute()
            parent_id = res.get('files', [{}])[0].get('id')
            
            sub_res = service.files().list(q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder'", fields="files(id, name)", orderBy="name").execute()
            subs = sub_res.get('files', [])
            
            if len(subs) >= 2:
                old_f, new_f = subs[-2], subs[-1]
                st.markdown(f"<div class='status-box'>📑 Comparing: <b>{old_f['name']}</b> ➔ <b>{new_f['name']}</b></div>", unsafe_allow_html=True)

                def get_detailed_data(f_id):
                    items = service.files().list(q=f"'{f_id}' in parents and name contains '.xlsx'", fields="files(id, name)").execute().get('files', [])
                    rows = []
                    for it in items:
                        req = service.files().get_media(fileId=it['id'])
                        fh = io.BytesIO(); MediaIoBaseDownload(fh, req).next_chunk(); fh.seek(0)
                        df = pd.read_excel(fh)
                        for _, r in df.iterrows():
                            # Re-applying mapping from your image
                            if len(df.columns) > 19 and 'episode' in str(df.columns[cx('T')]).lower():
                                rows.append({'ID': str(r.iloc[cx('T')]), 'Name': r.iloc[cx('V')], 'PHI': r.iloc[cx('Q')], 'TU': r.iloc[cx('P')], 'Outcome': r.iloc[cx('AE')], 'Report': it['name']})
                            elif len(df.columns) > 12 and 'episode' in str(df.columns[cx('M')]).lower():
                                rows.append({'ID': str(r.iloc[cx('M')]), 'Name': r.iloc[cx('N')], 'PHI': r.iloc[cx('E')], 'TU': r.iloc[cx('C')], 'Outcome': r.iloc[cx('BK')], 'Report': it['name']})
                            elif len(df.columns) > 10 and 'episode' in str(df.columns[cx('K')]).lower():
                                rows.append({'ID': str(r.iloc[cx('K')]), 'Name': r.iloc[cx('O')], 'PHI': r.iloc[cx('D')], 'TU': r.iloc[cx('C')], 'Outcome': r.iloc[cx('U')], 'Report': it['name']})
                    return pd.DataFrame(rows).drop_duplicates(subset=['ID'])

                with st.spinner("🔄 Comparing data..."):
                    df_old = get_detailed_data(old_f['id'])
                    df_new = get_detailed_data(new_f['id'])

                    persistent = df_new[df_new['ID'].isin(df_old['ID'])].copy()
                    persistent['Status'] = "🔴 Persistent"
                    new_entries = df_new[~df_new['ID'].isin(df_old['ID'])].copy()
                    new_entries['Status'] = "🔵 New"
                    resolved = df_old[~df_old['ID'].isin(df_new['ID'])].copy()
                    resolved['Status'] = "🟢 Resolved"

                    k1, k2, k3 = st.columns(3)
                    with k1: st.markdown(draw_card("Persistent", len(persistent), "#c0392b", "⚠️"), unsafe_allow_html=True)
                    with k2: st.markdown(draw_card("New Today", len(new_entries), "#1f618d", "🆕"), unsafe_allow_html=True)
                    with k3: st.markdown(draw_card("Resolved", len(resolved), "#27ae60", "✅"), unsafe_allow_html=True)

                    st.write("### Comparison Results")
                    final_view = pd.concat([persistent, new_entries])
                    st.dataframe(final_view[['Status', 'Name', 'Outcome', 'ID', 'TU', 'PHI', 'Report']], use_container_width=True, hide_index=True)
            else:
                st.error("Two folders required in Drive.")
        except Exception as e:
            st.error(f"Error: {e}")

st.markdown("<div class='amc-footer'>District TB Center Ahmedabad | AMC NTEP</div>", unsafe_allow_html=True)
