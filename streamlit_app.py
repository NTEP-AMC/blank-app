import streamlit as st
import pandas as pd
import os
import base64
import json
import io

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
    .block-container { padding-top: 1rem; max-width: 1200px; }
    .report-mini-box { background-color: #eaf2f8; border-left: 5px solid #1f618d; padding: 8px 15px; border-radius: 5px; margin: 5px; text-align: center; display: inline-block; min-width: 120px; font-size: 14px; font-weight: bold; color: #1f618d; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .status-persistent { color: #c0392b; font-weight: bold; }
    .status-new { color: #1f618d; font-weight: bold; }
    .status-resolved { color: #27ae60; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- HEADER LOGIC ---
def img_to_b64(path):
    try:
        with open(path, "rb") as f: return base64.b64encode(f.read()).decode()
    except: return None

b64_amc = img_to_b64('images/amc.png')
b64_ntep = img_to_b64('images/ntep.jpg')

img_amc_html = f"<img src='data:image/png;base64,{b64_amc}' height='60'>" if b64_amc else "🏢 <b>AMC</b>"
img_ntep_html = f"<img src='data:image/jpeg;base64,{b64_ntep}' height='60'>" if b64_ntep else "🏥 <b>NTEP</b>"

st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center;'>
    {img_amc_html}
    <h3 style='margin:0; color:#333; font-weight:900;'>AMC <span style='color:#ccc;'>|</span> NTEP</h3>
    {img_ntep_html}
</div>
<div style='background-color: #1f618d; color: white; text-align: center; padding: 8px; font-weight: bold; border-radius: 5px; margin: 10px 0;'>
   Unified TB Monitoring Dashboard - Ahmedabad
</div>
""", unsafe_allow_html=True)

# --- UTILS ---
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

# --- MAIN APP LOGIC ---
st.info("Click the button below to fetch today's registers from Google Drive and generate the Master Comparison.")

if st.button("🚀 Sync with Google Drive & Generate Report", use_container_width=True):
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 Google Drive Secrets are missing in Streamlit App Settings -> Secrets.")
    else:
        try:
            creds_info = json.loads(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
            service = build('drive', 'v3', credentials=creds)
            
            res = service.files().list(q="name='AMC_NTEP_Data' and mimeType='application/vnd.google-apps.folder'", fields="files(id)").execute()
            p_id = res.get('files', [{}])[0].get('id')
            subs = service.files().list(q=f"'{p_id}' in parents", fields="files(id, name)", orderBy="name").execute().get('files', [])
            
            if len(subs) >= 2:
                old_f, new_f = subs[-2], subs[-1]
                
                # Download and map function
                def get_drive_data(f_id):
                    items = service.files().list(q=f"'{f_id}' in parents and name contains '.xlsx'", fields="files(id, name)").execute().get('files', [])
                    rows = []
                    for it in items:
                        req = service.files().get_media(fileId=it['id'])
                        fh = io.BytesIO(); MediaIoBaseDownload(fh, req).next_chunk(); fh.seek(0)
                        df = pd.read_excel(fh)
                        
                        for _, r in df.iterrows():
                            # MAPPING BASED ON YOUR COLUMNS
                            if len(df.columns) > 19:
                                r_type = "Lab Pending"
                                id_c, nm_c, ph_c, tu_c, dg_c, ot_c = 'T', 'V', 'Q', 'P', 'A', 'AE'
                            elif len(df.columns) > 12:
                                r_type = "Notification"
                                id_c, nm_c, ph_c, tu_c, dg_c, ot_c = 'M', 'N', 'E', 'C', 'S', 'BK'
                            else:
                                r_type = "Co-morbidity"
                                id_c, nm_c, ph_c, tu_c, dg_c, ot_c = 'K', 'O', 'D', 'C', 'M', 'U'
                                
                            rows.append({
                                'EPISODE ID': str(r.iloc[cx(id_c)]), 'PATIENT NAME': r.iloc[cx(nm_c)], 
                                'PHI': r.iloc[cx(ph_c)], 'TB UNIT': r.iloc[cx(tu_c)], 
                                'DIAGNOSIS DATE': r.iloc[cx(dg_c)], 'TREATMENT OUTCOME': r.iloc[cx(ot_c)], 
                                'REPORT TYPE': r_type
                            })
                    return pd.DataFrame(rows).drop_duplicates(subset=['EPISODE ID'])

                with st.spinner("🔄 Downloading and analyzing records from Google Drive..."):
                    df_old = get_drive_data(old_f['id'])
                    df_new = get_drive_data(new_f['id'])
                    
                    # --- NIKSHAY ERROR HANDLING LOGIC ---
                    # Only compare the registers that successfully uploaded today
                    latest_registers = df_new['REPORT TYPE'].unique()
                    df_old_filtered = df_old[df_old['REPORT TYPE'].isin(latest_registers)]
                    
                    # Comparison Math
                    persistent = df_new[df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
                    persistent['STATUS'] = "🔴 Persistent"
                    
                    new_pat = df_new[~df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
                    new_pat['STATUS'] = "🔵 New Entry"
                    
                    resolved = df_old_filtered[~df_old_filtered['EPISODE ID'].isin(df_new['EPISODE ID'])].copy()
                    resolved['STATUS'] = "🟢 Resolved"

                    # Build final view
                    res_final = pd.concat([persistent, new_pat, resolved])
                    
                    # Zone Mapping (Try local file if it exists, otherwise leave empty)
                    try:
                        df_zone = pd.read_excel("data/zone_mapping.xlsx", usecols=[0, 1])
                        df_zone.columns = ['PHI_Map', 'ZONE']
                        res_final = res_final.merge(df_zone, left_on='PHI', right_on='PHI_Map', how='left').drop(columns=['PHI_Map'])
                        res_final['ZONE'] = res_final['ZONE'].fillna("Unknown")
                    except:
                        res_final['ZONE'] = "Not Mapped"

                    # Calculate Top Numbers (Based on today's pending: Persistent + New)
                    today_pending = pd.concat([persistent, new_pat])
                    unique_patients = today_pending['EPISODE ID'].nunique()
                    total_pendency = len(today_pending)

                    # Dynamic Mini-Boxes for Report Counts
                    counts = today_pending['REPORT TYPE'].value_counts().to_dict()

                    st.success(f"✅ Success! Compared **{old_f['name']}** vs **{new_f['name']}**.")
                    st.warning(f"📝 **Registers Processed Today:** {', '.join(latest_registers)}")

                    # UI - Top Cards
                    c1, c2, c3 = st.columns(3)
                    with c1: st.markdown(draw_card("Total Pending Today", total_pendency, "#1f618d", "📋"), unsafe_allow_html=True)
                    with c2: st.markdown(draw_card("New Entries", len(new_pat), "#2980b9", "🆕"), unsafe_allow_html=True)
                    with c3: st.markdown(draw_card("Resolved / Cleared", len(resolved), "#27ae60", "✅"), unsafe_allow_html=True)

                    # UI - Mini Boxes
                    html_boxes = "".join([f"<div class='report-mini-box'>{k}: {v}</div>" for k, v in counts.items() if v > 0])
                    st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'>{html_boxes}</div>", unsafe_allow_html=True)

                    # UI - Data Table
                    st.write("### 🔍 Unified Patient Action List")
                    # Reorder columns as requested
                    display_cols = ['STATUS', 'ZONE', 'TB UNIT', 'PHI', 'EPISODE ID', 'PATIENT NAME', 'DIAGNOSIS DATE', 'TREATMENT OUTCOME', 'REPORT TYPE']
                    st.dataframe(res_final[display_cols], use_container_width=True, hide_index=True)
                    
            else: st.error("Need at least 2 date-named folders in Google Drive to run a comparison.")
        except Exception as e: st.error(f"Error connecting to Google Drive: {e}")

st.markdown("<div style='text-align: center; font-size: 11px; margin-top: 30px; color: #888;'>District TB Center AMC | Unified Cloud Dashboard v6.0</div>", unsafe_allow_html=True)
