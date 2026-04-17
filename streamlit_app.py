import streamlit as st
import pandas as pd
import glob
import os
from datetime import date
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
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 800px; }
    .amc-footer { text-align: center; font-size: 11px; color: #555; margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 1. LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center; color: #1f618d;'>🏥 AMC NTEP Login</h2>", unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if pwd == "AMC@2026": st.session_state.auth = True; st.rerun()
        else: st.error("Wrong Password")
    st.stop()

# --- HELPER: IMAGE TO HTML CONVERTER ---
def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

b64_amc = img_to_b64("images/amc.png")
b64_ntep = img_to_b64("images/ntep.jpg")
b64_h1 = img_to_b64("images/h1.jpg")
b64_h2 = img_to_b64("images/h2.jpg")

src_amc = f"data:image/png;base64,{b64_amc}" if b64_amc else ""
src_ntep = f"data:image/jpeg;base64,{b64_ntep}" if b64_ntep else ""
src_h1 = f"data:image/jpeg;base64,{b64_h1}" if b64_h1 else ""
src_h2 = f"data:image/jpeg;base64,{b64_h2}" if b64_h2 else ""

# Official Logos & Banner
st.markdown(f"""
<div style='display: flex; justify-content: space-between; align-items: center; padding: 0 10px;'>
    <img src='{src_amc}' height='75'>
    <h3 style='margin:0; color:#333; font-weight:900;'>AMC <span style='color:#ccc;'>|</span> NTEP</h3>
    <img src='{src_ntep}' height='75'>
</div>
<div style='background-color: #1f618d; color: white; text-align: center; padding: 12px; font-weight: bold; font-size: 18px; border-radius: 5px; margin-top: 15px; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
   TB Monitoring Dashboard - Ahmedabad
</div>
<div style='display: flex; gap: 8px; margin-bottom: 20px;'>
    <img src='{src_h1}' style='width: 50%; height: 130px; object-fit: cover; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
    <img src='{src_h2}' style='width: 50%; height: 130px; object-fit: cover; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);'>
</div>
""", unsafe_allow_html=True)

# Create the Tabs!
tab1, tab2 = st.tabs(["📊 Master Dashboard (Local)", "📈 Daily Comparison (Google Drive)"])

# ==========================================
# TAB 1: YOUR EXISTING MASTER DASHBOARD
# ==========================================
with tab1:
    def cx(col_letter):
        num = 0
        for c in col_letter.upper(): num = num * 26 + (ord(c) - ord('A') + 1)
        return num - 1

    def get_col(df, letter):
        if not letter: return pd.Series([""] * len(df))
        idx = cx(letter)
        if idx < len(df.columns): return df.iloc[:, idx].astype(str).fillna("")
        return pd.Series([""] * len(df))

    def is_blank(series):
        return series.str.strip().str.lower().isin(["", "nan", "nat", "none", "<na>", "null"])

    @st.cache_data
    def process_data():
        files = glob.glob("data/*.xlsx")
        df_slpa, df_udst, df_npo, df_op, df_cp = [pd.DataFrame()] * 5
        df_adt, df_rbs, df_art, df_cpt, df_hiv = [pd.DataFrame()] * 5
        
        df_z = pd.DataFrame()
        for f in files:
            if "zone" in f.lower() and "~$" not in f:
                try:
                    df_z = pd.read_excel(f, usecols=[0,1])
                    df_z.columns = ['PHI_Map', 'Zone_Map']
                    df_z['PHI_Map'] = df_z['PHI_Map'].astype(str).str.strip().str.upper()
                except: pass

        for f in files:
            fname = os.path.basename(f).lower()
            if "zone" in fname or "~$" in fname: continue
            
            df = pd.read_excel(f, header=0)
            if df.empty: continue
            
            def col_name(letter):
                idx = cx(letter)
                return str(df.columns[idx]).lower() if idx < len(df.columns) else ""

            file_type = "UNKNOWN"
            if "episode" in col_name('T'): file_type = "LAB"
            elif "episode" in col_name('M'): file_type = "NOTIF"
            elif "episode" in col_name('I'): file_type = "CONSENT"
            elif "episode" in col_name('K'): file_type = "COMORB"
            else: continue

            id_letter = {'LAB': 'T', 'NOTIF': 'M', 'CONSENT': 'I', 'COMORB': 'K'}[file_type]
            df['Standard_ID'] = get_col(df, id_letter).astype(str).str.strip().str.upper()
            df = df[~is_blank(df['Standard_ID'])]
            df = df.drop_duplicates(subset=['Standard_ID'], keep='last')

            base_cols = ['ZONE', 'TB Unit', 'Facility Type', 'PHI', 'Patient Name', 'Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date']
            
            def finalize_df(filtered_df, id_let, name_let, tu_let, phi_let, type_let, diag_let, init_let, out_let):
                if filtered_df.empty: return pd.DataFrame(columns=base_cols)
                clean_df = pd.DataFrame({
                    'Episode ID': filtered_df['Standard_ID'], 'Patient Name': get_col(filtered_df, name_let),
                    'TB Unit': get_col(filtered_df, tu_let), 'PHI': get_col(filtered_df, phi_let),
                    'Facility Type': get_col(filtered_df, type_let), 'Diagnosis Date': get_col(filtered_df, diag_let),
                    'Initiation Date': get_col(filtered_df, init_let), 'Outcome Date': get_col(filtered_df, out_let)
                })
                clean_df['merge_key'] = clean_df['PHI'].astype(str).str.strip().str.upper()
                if not df_z.empty:
                    merged = clean_df.merge(df_z, left_on='merge_key', right_on='PHI_Map', how='left')
                    merged['ZONE'] = merged['Zone_Map'].fillna("Zone Not Found")
                else: merged = clean_df.assign(ZONE="No Zone File")
                return merged[base_cols]

            if file_type == "LAB":
                site_c = get_col(df, 'F').str.lower()
                is_pulm = site_c.str.contains("pulmonary", na=False) & ~site_c.str.contains("extra", na=False)
                is_udst = is_pulm & is_blank(get_col(df, 'AQ')) & is_blank(get_col(df, 'AU')) & is_blank(get_col(df, 'BC'))
                df_udst = finalize_df(df[is_udst], 'T', 'V', 'P', 'Q', 'R', 'A', 'B', 'AF')

                has_rif = get_col(df, 'AR').str.lower().str.contains("rif resistance detected", na=False) | get_col(df, 'AZ').str.lower().str.contains("rif resistance detected", na=False) | get_col(df, 'BD').str.lower().str.contains("rif resistance detected", na=False)
                has_inh = get_col(df, 'DO').str.lower().str.contains("inh resistance", na=False)
                is_slpa = is_pulm & (has_rif | has_inh) & is_blank(get_col(df, 'BH'))
                df_slpa = finalize_df(df[is_slpa], 'T', 'V', 'P', 'Q', 'R', 'A', 'B', 'AF')

            elif file_type == "NOTIF":
                out_c = get_col(df, 'BK')
                init_c = get_col(df, 'BM')
                reg_c = pd.Series([""] * len(df))
                for col in df.columns:
                    if "regimen" in str(col).lower():
                        reg_c = df[col].astype(str).str.upper().str.replace(" ", "")
                        break
                df_npo = finalize_df(df[is_blank(init_c) & is_blank(out_c)], 'M', 'N', 'C', 'E', 'D', 'S', 'BM', 'CB')
                df_op = finalize_df(df[is_blank(out_c) & (reg_c == "2HRZE/4HRE")], 'M', 'N', 'C', 'E', 'D', 'S', 'BM', 'CB')

            elif file_type == "CONSENT":
                df_cp = finalize_df(df[is_blank(get_col(df, 'Y'))], 'I', 'J', 'V', 'W', 'X', 'G', None, None)

            elif file_type == "COMORB":
                am, an, ah = get_col(df, 'AM').str.strip().str.lower(), get_col(df, 'AN').str.strip(), get_col(df, 'AH').str.strip().str.lower()
                al, ak, ai = get_col(df, 'AL').str.strip(), get_col(df, 'AK').str.strip(), get_col(df, 'AI').str.strip()
                is_hiv_reactive = ah.isin(["reactive", "positive"])

                df_adt = finalize_df(df[(am == "diabetic") & is_blank(an)], 'K', 'O', 'C', 'D', None, 'M', 'W', None)
                df_rbs = finalize_df(df[am.isin(["unknown", ""]) | is_blank(am)], 'K', 'O', 'C', 'D', None, 'M', 'W', None)
                df_art = finalize_df(df[is_hiv_reactive & is_blank(al)], 'K', 'O', 'C', 'D', None, 'M', 'W', None)
                df_cpt = finalize_df(df[is_hiv_reactive & is_blank(ak)], 'K', 'O', 'C', 'D', None, 'M', 'W', None)
                df_hiv = finalize_df(df[is_blank(ai)], 'K', 'O', 'C', 'D', None, 'M', 'W', None)

        all_raw_dfs = [df_slpa, df_udst, df_npo, df_op, df_cp, df_adt, df_rbs, df_art, df_cpt, df_hiv]
        for d in all_raw_dfs:
            if not d.empty: 
                d['Diagnosis Date'] = pd.to_datetime(d['Diagnosis Date'], errors='coerce')
                d['Initiation Date'] = pd.to_datetime(d['Initiation Date'], errors='coerce')
                d['Outcome Date'] = pd.to_datetime(d['Outcome Date'], errors='coerce')
        return tuple(all_raw_dfs)

    (f_slpa, f_udst, f_npo, f_op, f_cp, f_adt, f_rbs, f_art, f_cpt, f_hiv) = process_data()

    master_reports = {
        "SLPA": {"df": f_slpa, "icon": "🔬", "color": "#D35400"}, "UDST": {"df": f_udst, "icon": "🧪", "color": "#C0392B"}, 
        "Not Put On": {"df": f_npo, "icon": "⏳", "color": "#27AE60"}, "Outcome": {"df": f_op, "icon": "🏥", "color": "#F39C12"}, 
        "Consent": {"df": f_cp, "icon": "📝", "color": "#8E44AD"}, "ADT": {"df": f_adt, "icon": "🩸", "color": "#16A085"},
        "RBS": {"df": f_rbs, "icon": "💉", "color": "#E67E22"}, "ART": {"df": f_art, "icon": "💊", "color": "#2980B9"},
        "CPT": {"df": f_cpt, "icon": "🛡️", "color": "#D35400"}, "HIV": {"df": f_hiv, "icon": "🩺", "color": "#C0392B"}
    }

    pieces = []
    for rep_name, info in master_reports.items():
        if not info["df"].empty:
            temp = info["df"].copy()
            temp['Pending Status'] = rep_name
            pieces.append(temp)

    if pieces:
        all_pendencies = pd.concat(pieces)
        df_master = all_pendencies.groupby('Episode ID').agg({
            'Patient Name': 'first', 'ZONE': 'first', 'TB Unit': 'first', 'PHI': 'first',
            'Facility Type': 'first', 'Diagnosis Date': 'first', 'Initiation Date': 'first', 'Outcome Date': 'first',
            'Pending Status': lambda x: " + ".join(x.unique())
        }).reset_index()
    else: df_master = pd.DataFrame(columns=['Episode ID', 'Patient Name', 'ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Pending Status'])

    df_master = df_master[['ZONE', 'TB Unit', 'Facility Type', 'PHI', 'Patient Name', 'Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Pending Status']]

    def get_opts(df, col):
        if df.empty or col not in df.columns: return []
        return sorted([str(x) for x in df[col].unique() if str(x).strip() not in ["", "nan", "None", "Zone Not Found", "N/A"]])

    with st.expander("🔽 Filters & Sorting"):
        f_rep = st.multiselect("Report Type", list(master_reports.keys()), placeholder="All Reports")
        col1, col2 = st.columns(2)
        with col1:
            sel_zone = st.multiselect("Zone", get_opts(df_master, 'ZONE'))
            df_for_tu = df_master[df_master['ZONE'].isin(sel_zone)] if sel_zone else df_master
            sel_tu = st.multiselect("TB Unit", get_opts(df_for_tu, 'TB Unit'))
        with col2:
            df_for_type = df_for_tu[df_for_tu['TB Unit'].isin(sel_tu)] if sel_tu else df_for_tu
            sel_type = st.multiselect("Facility Type", get_opts(df_for_type, 'Facility Type'))
            df_for_phi = df_for_type[df_for_type['Facility Type'].isin(sel_type)] if sel_type else df_for_type
            sel_phi = st.multiselect("PHI", get_opts(df_for_phi, 'PHI'))

        if st.button("Reset Filters", use_container_width=True): st.rerun()

    df_display = df_master.copy()
    if not df_display.empty:
        if sel_zone: df_display = df_display[df_display['ZONE'].isin(sel_zone)]
        if sel_tu: df_display = df_display[df_display['TB Unit'].isin(sel_tu)]
        if sel_type: df_display = df_display[df_display['Facility Type'].isin(sel_type)]
        if sel_phi: df_display = df_display[df_display['PHI'].isin(sel_phi)]
        if len(f_rep) > 0:
            pattern = "|".join(f_rep)
            df_display = df_display[df_display['Pending Status'].str.contains(pattern, regex=True, na=False)]

    total_unique_patients = len(df_display)

    def draw_card(title, value, color, icon):
        return f"""
        <div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="font-size: 24px; margin-bottom: 5px;">{icon}</div>
            <div style="font-size: 13px; font-weight: bold; text-transform: uppercase; line-height: 1.1;">{title}</div>
            <div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div>
        </div>
        """
    r1_c1, r1_c2 = st.columns(2)
    with r1_c1: st.markdown(draw_card("Total Pending Patients", total_unique_patients, "#1f618d", "👥"), unsafe_allow_html=True)
    with r1_c2: st.markdown(draw_card("UDST Pending", len(df_display[df_display['Pending Status'].str.contains('UDST', na=False)]), "#C0392B", "🧪"), unsafe_allow_html=True)

    st.markdown("<h4 style='color: #444; margin-top: 10px;'>Patient Line List</h4>", unsafe_allow_html=True)
    search_query = st.text_input("🔍 Search Patient Name or Episode ID", "")
    if search_query: df_display = df_display[df_display['Patient Name'].str.contains(search_query, case=False, na=False) | df_display['Episode ID'].str.contains(search_query, case=False, na=False)]

    conf = {"Diagnosis Date": st.column_config.DateColumn(format="YYYY-MM-DD"), "Initiation Date": st.column_config.DateColumn(format="YYYY-MM-DD"), "Outcome Date": st.column_config.DateColumn(format="YYYY-MM-DD")}
    st.dataframe(df_display, use_container_width=True, hide_index=True, column_config=conf, height=400)


# ==========================================
# TAB 2: NEW GOOGLE DRIVE COMPARISON
# ==========================================
with tab2:
    st.markdown("<h3 style='color: #1f618d;'>Cloud Data Comparison</h3>", unsafe_allow_html=True)
    st.write("This engine securely reads your daily Google Drive folders to track resolved vs. persistent patients.")
    
    if st.button("🔄 Run Daily Comparison Tracker", use_container_width=True):
        try:
            # 1. Connect using the Secret Key
            creds_info = json.loads(st.secrets["gcp_service_account"])
            creds = service_account.Credentials.from_service_account_info(creds_info, scopes=['https://www.googleapis.com/auth/drive.readonly'])
            service = build('drive', 'v3', credentials=creds)
            
            # 2. Find the main AMC folder
            results = service.files().list(q="name='AMC_NTEP_Data' and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)").execute()
            folders = results.get('files', [])
            
            if not folders:
                st.error("❌ Could not find a folder named exactly 'AMC_NTEP_Data' in the shared Google Drive.")
            else:
                parent_id = folders[0]['id']
                
                # 3. Get all daily date folders inside it
                sub_results = service.files().list(q=f"'{parent_id}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false", fields="files(id, name)", orderBy="name").execute()
                subfolders = sub_results.get('files', [])
                
                if len(subfolders) < 2:
                    st.warning(f"Found {len(subfolders)} daily folder(s). You need at least 2 date folders (like 2026-04-13 and 2026-04-17) to compare.")
                else:
                    # Grab the two most recent dates
                    old_folder = subfolders[-2]
                    new_folder = subfolders[-1]
                    st.success(f"✅ Found data! Comparing **{old_folder['name']}** (Old) vs **{new_folder['name']}** (New)")
                    
                    # Tool to extract all Episode IDs from a folder
                    def get_ids_from_folder(folder_id):
                        files_res = service.files().list(q=f"'{folder_id}' in parents and name contains '.xlsx' and trashed=false", fields="files(id, name)").execute()
                        files = files_res.get('files', [])
                        all_ids = set()
                        for f in files:
                            request = service.files().get_media(fileId=f['id'])
                            fh = io.BytesIO()
                            downloader = MediaIoBaseDownload(fh, request)
                            done = False
                            while done is False: status, done = downloader.next_chunk()
                            fh.seek(0)
                            
                            df = pd.read_excel(fh)
                            # Hunt for the "Episode ID" column automatically
                            for col in df.columns:
                                if 'episode' in str(col).lower():
                                    ids = df[col].astype(str).str.strip().str.upper()
                                    ids = ids[~ids.isin(["", "NAN", "NAT", "NONE", "<NA>", "NULL"])]
                                    all_ids.update(ids.tolist())
                                    break
                        return all_ids

                    with st.spinner("Downloading and comparing data... (This takes a few seconds)"):
                        old_ids = get_ids_from_folder(old_folder['id'])
                        new_ids = get_ids_from_folder(new_folder['id'])
                        
                        persistent_ids = old_ids.intersection(new_ids)
                        cleared_ids = old_ids - new_ids
                        newly_added_ids = new_ids - old_ids
                        
                        st.markdown("---")
                        c1, c2, c3 = st.columns(3)
                        c1.markdown(draw_card("🔴 Persistent (Stuck)", len(persistent_ids), "#C0392B", "⚠️"), unsafe_allow_html=True)
                        c2.markdown(draw_card("🟢 Cleared (Resolved)", len(cleared_ids), "#27AE60", "✅"), unsafe_allow_html=True)
                        c3.markdown(draw_card("🔵 New Entries", len(newly_added_ids), "#2980B9", "🆕"), unsafe_allow_html=True)
                        
                        st.write("### 🔴 Persistent Patients")
                        st.caption("These Episode IDs were pending yesterday AND are still pending today.")
                        st.dataframe(pd.DataFrame(list(persistent_ids), columns=["Episode ID"]), use_container_width=True)
                        
        except Exception as e:
            st.error(f"Something went wrong connecting to Drive: {e}")
            st.write("Did you paste the Secret Key correctly in Streamlit Settings?")

# --- 9. OFFICIAL FOOTER ---
st.markdown("<div class='amc-footer'>Created by District TB Center AMC | NTEP Monitoring System</div>", unsafe_allow_html=True)
