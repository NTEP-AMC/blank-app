import streamlit as st
import pandas as pd
import json
import io

# --- GOOGLE DRIVE TOOLS ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="AMC NTEP", layout="wide", initial_sidebar_state="collapsed")

# --- ULTRA SIMPLE CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1rem; max-width: 1200px; }
    .big-font { font-size: 20px !important; font-weight: bold; color: #333; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #1f618d; border-bottom: 2px solid #1f618d; padding-bottom: 10px;'>🏥 AMC NTEP | Daily Monitoring Dashboard</h2>", unsafe_allow_html=True)

# --- UTILS ---
def cx(letter):
    num = 0
    for c in letter.upper(): num = num * 26 + (ord(c) - ord('A') + 1)
    return num - 1

def draw_card(title, value, color):
    return f"""
    <div style="background-color: {color}; border-radius: 5px; padding: 15px; color: white; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
        <div style="font-size: 14px; font-weight: bold; text-transform: uppercase;">{title}</div>
        <div style="font-size: 36px; font-weight: 900; margin-top: 5px;">{value}</div>
    </div>
    """

def get_credentials():
    secret_val = st.secrets["gcp_service_account"]
    if isinstance(secret_val, str):
        cleaned_str = secret_val.replace("'", '"')
        return json.loads(cleaned_str)
    return dict(secret_val)

# --- MEMORY CACHE LOGIC (SPEED FIX) ---
# This memorizes the data for 12 hours so it doesn't download it twice
@st.cache_data(ttl=43200, show_spinner=False)
def get_drive_data(f_id, _creds_info):
    creds = service_account.Credentials.from_service_account_info(_creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    service = build('drive', 'v3', credentials=creds)
    
    items = service.files().list(q=f"'{f_id}' in parents and name contains '.xlsx'", fields="files(id, name)").execute().get('files', [])
    rows = []
    
    for it in items:
        req = service.files().get_media(fileId=it['id'])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)
        df = pd.read_excel(fh)
        
        for _, r in df.iterrows():
            if len(df.columns) > 19:
                r_type, id_c, nm_c, ph_c, tu_c, dg_c, ot_c = "Lab Pending", 'T', 'V', 'Q', 'P', 'A', 'AE'
            elif len(df.columns) > 12:
                r_type, id_c, nm_c, ph_c, tu_c, dg_c, ot_c = "Notification", 'M', 'N', 'E', 'C', 'S', 'BK'
            else:
                r_type, id_c, nm_c, ph_c, tu_c, dg_c, ot_c = "Co-morbidity", 'K', 'O', 'D', 'C', 'M', 'U'
                
            rows.append({
                'EPISODE ID': str(r.iloc[cx(id_c)]), 'PATIENT NAME': r.iloc[cx(nm_c)], 
                'PHI': r.iloc[cx(ph_c)], 'TB UNIT': r.iloc[cx(tu_c)], 
                'DIAGNOSIS DATE': r.iloc[cx(dg_c)], 'OUTCOME': r.iloc[cx(ot_c)], 
                'REGISTER': r_type
            })
    return pd.DataFrame(rows).drop_duplicates(subset=['EPISODE ID'])

# --- MAIN APP LOGIC ---
st.markdown("<p class='big-font' style='text-align: center;'>Click the button below to fetch today's data directly from Google Drive.</p>", unsafe_allow_html=True)

col1, col2 = st.columns([4, 1])
with col1:
    run_btn = st.button("🚀 FETCH AND ANALYZE TODAY'S DATA", use_container_width=True, type="primary")
with col2:
    if st.button("🗑️ Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Memory cleared!")

if run_btn:
    if "gcp_service_account" not in st.secrets:
        st.error("🚨 Google Drive Secrets are missing in Streamlit App Settings -> Secrets.")
    else:
        try:
            creds_info = get_credentials()
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
            service = build('drive', 'v3', credentials=creds)
            
            res = service.files().list(q="name='AMC_NTEP_Data' and mimeType='application/vnd.google-apps.folder'", fields="files(id)").execute()
            p_id = res.get('files', [{}])[0].get('id')
            subs = service.files().list(q=f"'{p_id}' in parents", fields="files(id, name)", orderBy="name").execute().get('files', [])
            
            if len(subs) >= 2:
                old_f, new_f = subs[-2], subs[-1]
                
                with st.status("🔄 Downloading heavy files from Google Drive... (This takes 20 seconds the first time)", expanded=True) as status:
                    st.write(f"Reading folder: {old_f['name']}...")
                    df_old = get_drive_data(old_f['id'], creds_info)
                    
                    st.write(f"Reading folder: {new_f['name']}...")
                    df_new = get_drive_data(new_f['id'], creds_info)
                    
                    status.update(label="✅ Download complete! Comparing data...", state="complete", expanded=False)
                    
                # Smart Filter: Only compare registers uploaded today
                latest_registers = df_new['REGISTER'].unique()
                df_old_filtered = df_old[df_old['REGISTER'].isin(latest_registers)]
                
                persistent = df_new[df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
                persistent['STATUS'] = "🔴 Persistent"
                
                new_pat = df_new[~df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
                new_pat['STATUS'] = "🔵 New Entry"
                
                resolved = df_old_filtered[~df_old_filtered['EPISODE ID'].isin(df_new['EPISODE ID'])].copy()
                resolved['STATUS'] = "🟢 Resolved"

                res_final = pd.concat([persistent, new_pat, resolved])

                st.write(f"**Registers Checked Today:** {', '.join(latest_registers)}")

                # UI - Top Cards
                c1, c2, c3 = st.columns(3)
                with c1: st.markdown(draw_card("Total Pending", len(persistent) + len(new_pat), "#1f618d"), unsafe_allow_html=True)
                with c2: st.markdown(draw_card("New Today", len(new_pat), "#2980b9"), unsafe_allow_html=True)
                with c3: st.markdown(draw_card("Resolved / Cleared", len(resolved), "#27ae60"), unsafe_allow_html=True)

                st.write("---")
                st.write("### 📋 Unified Action List")
                display_cols = ['STATUS', 'TB UNIT', 'PHI', 'EPISODE ID', 'PATIENT NAME', 'DIAGNOSIS DATE', 'OUTCOME', 'REGISTER']
                st.dataframe(res_final[display_cols], use_container_width=True, hide_index=True)
                
            else: st.error("Missing Data: Please ensure at least 2 date-named folders exist in Google Drive.")
        except json.JSONDecodeError:
            st.error("🚨 **Google Drive Key Error:** The secret key is still formatted incorrectly in Streamlit Settings.")
        except Exception as e: 
            st.error(f"Error connecting to Google Drive: {e}")
