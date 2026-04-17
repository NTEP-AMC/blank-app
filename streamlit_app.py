import streamlit as st
import pandas as pd
import json
import io

# --- GOOGLE DRIVE TOOLS ---
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

st.set_page_config(page_title="AMC NTEP", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1rem; max-width: 1200px; }
    .big-font { font-size: 18px !important; font-weight: bold; color: #333; }
    .report-mini-box { background-color: #eaf2f8; border-left: 5px solid #1f618d; padding: 8px 15px; border-radius: 5px; margin: 5px; text-align: center; display: inline-block; min-width: 120px; font-size: 14px; font-weight: bold; color: #1f618d; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
</style>
""", unsafe_allow_html=True)

st.markdown("<h2 style='text-align: center; color: #1f618d; border-bottom: 2px solid #1f618d; padding-bottom: 10px;'>🏥 AMC NTEP | Unified Monitoring Dashboard</h2>", unsafe_allow_html=True)

# --- UTILS & CARDS ---
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

# --- SMART COLUMN EXTRACTOR ---
# This searches for keywords in the header instead of relying on column letters
def safe_extract(df, keywords):
    for kw in keywords:
        matches = [col for col in df.columns if kw.lower() in str(col).lower()]
        if matches: return df[matches[0]].astype(str).replace('nan', '')
    return pd.Series([""] * len(df))

@st.cache_data(ttl=43200, show_spinner=False)
def get_drive_data(f_id, _creds_info):
    creds = service_account.Credentials.from_service_account_info(_creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
    service = build('drive', 'v3', credentials=creds)
    
    items = service.files().list(q=f"'{f_id}' in parents and name contains '.xlsx'", fields="files(id, name)").execute().get('files', [])
    all_rows = []
    
    for it in items:
        req = service.files().get_media(fileId=it['id'])
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done: _, done = downloader.next_chunk()
        fh.seek(0)
        
        # Read excel, ensuring header is read correctly
        df = pd.read_excel(fh)
        
        # Identify Report Type by width (Nikshay standard)
        if len(df.columns) > 19: r_type = "Lab Pending"
        elif len(df.columns) > 12: r_type = "Notification"
        else: r_type = "Co-morbidity"
        
        # Smart Extraction
        ep_id = safe_extract(df, ['episode'])
        name = safe_extract(df, ['patient name', 'patient_name', 'name'])
        phi = safe_extract(df, ['phi', 'health facility', 'facility'])
        tbu = safe_extract(df, ['tbu', 'tb unit', 'unit'])
        diag_date = safe_extract(df, ['diagnosis date', 'diagnosis_date', 'initiation'])
        outcome = safe_extract(df, ['outcome'])
        
        temp_df = pd.DataFrame({
            'EPISODE ID': ep_id, 'PATIENT NAME': name, 'PHI': phi, 
            'TB UNIT': tbu, 'DIAGNOSIS DATE': diag_date, 'OUTCOME': outcome, 
            'REGISTER': r_type
        })
        all_rows.append(temp_df)
        
    if all_rows:
        return pd.concat(all_rows).drop_duplicates(subset=['EPISODE ID'])
    return pd.DataFrame()

# --- MAIN UI ---
col_btn1, col_btn2 = st.columns([4, 1])
with col_btn1:
    run_btn = st.button("🚀 FETCH AND ANALYZE TODAY'S DATA", use_container_width=True, type="primary")
with col_btn2:
    if st.button("🗑️ Clear Cache", use_container_width=True):
        st.cache_data.clear()
        st.success("Memory cleared!")

if run_btn:
    try:
        creds_info = get_credentials()
        creds = service_account.Credentials.from_service_account_info(creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
        service = build('drive', 'v3', credentials=creds)
        
        res = service.files().list(q="name='AMC_NTEP_Data' and mimeType='application/vnd.google-apps.folder'", fields="files(id)").execute()
        p_id = res.get('files', [{}])[0].get('id')
        subs = service.files().list(q=f"'{p_id}' in parents", fields="files(id, name)", orderBy="name").execute().get('files', [])
        
        if len(subs) >= 2:
            old_f, new_f = subs[-2], subs[-1]
            
            with st.status(f"🔄 Reading data from {new_f['name']}...", expanded=True) as status:
                df_old = get_drive_data(old_f['id'], creds_info)
                df_new = get_drive_data(new_f['id'], creds_info)
                status.update(label="✅ Data mapping and comparison complete!", state="complete", expanded=False)
                
            # Filter logic
            latest_registers = df_new['REGISTER'].unique()
            df_old_filtered = df_old[df_old['REGISTER'].isin(latest_registers)]
            
            persistent = df_new[df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
            persistent['STATUS'] = "🔴 Persistent"
            
            new_pat = df_new[~df_new['EPISODE ID'].isin(df_old_filtered['EPISODE ID'])].copy()
            new_pat['STATUS'] = "🔵 New Entry"
            
            resolved = df_old_filtered[~df_old_filtered['EPISODE ID'].isin(df_new['EPISODE ID'])].copy()
            resolved['STATUS'] = "🟢 Resolved"

            res_final = pd.concat([persistent, new_pat, resolved])
            today_active = pd.concat([persistent, new_pat]) # Only active pendency for KPI

            # --- KPI CARDS & MINI BOXES ---
            c1, c2, c3 = st.columns(3)
            with c1: st.markdown(draw_card("Total Active Pendency", len(today_active), "#1f618d"), unsafe_allow_html=True)
            with c2: st.markdown(draw_card("New Today", len(new_pat), "#2980b9"), unsafe_allow_html=True)
            with c3: st.markdown(draw_card("Resolved Today", len(resolved), "#27ae60"), unsafe_allow_html=True)

            # Generate Report-wise Mini Boxes dynamically
            counts = today_active['REGISTER'].value_counts().to_dict()
            html_boxes = "".join([f"<div class='report-mini-box'>{k}: {v}</div>" for k, v in counts.items()])
            st.markdown(f"<div style='text-align: center; margin-bottom: 20px;'>{html_boxes}</div>", unsafe_allow_html=True)

            st.write("---")
            
            # --- FILTERS ---
            with st.expander("🔎 Filter & Sort Data", expanded=True):
                f_col1, f_col2, f_col3 = st.columns(3)
                sel_status = f_col1.multiselect("Filter by Status", res_final['STATUS'].unique(), default=res_final['STATUS'].unique())
                sel_reg = f_col2.multiselect("Filter by Register", res_final['REGISTER'].unique())
                
                # Clean up TBU list for filter (remove blanks)
                tbu_list = [t for t in res_final['TB UNIT'].unique() if t.strip()]
                sel_tbu = f_col3.multiselect("Filter by TB Unit", sorted(tbu_list))

            # Apply Filters
            filtered_df = res_final[res_final['STATUS'].isin(sel_status)]
            if sel_reg: filtered_df = filtered_df[filtered_df['REGISTER'].isin(sel_reg)]
            if sel_tbu: filtered_df = filtered_df[filtered_df['TB UNIT'].isin(sel_tbu)]

            st.write(f"### 📋 Unified Action List ({len(filtered_df)} Patients)")
            display_cols = ['STATUS', 'TB UNIT', 'PHI', 'EPISODE ID', 'PATIENT NAME', 'DIAGNOSIS DATE', 'OUTCOME', 'REGISTER']
            st.dataframe(filtered_df[display_cols], use_container_width=True, hide_index=True)
            
        else: st.error("Need 2 folders in Google Drive to run comparison.")
    except Exception as e: st.error(f"Error: {e}")
