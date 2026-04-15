import streamlit as st
import pandas as pd
import glob
import os
from datetime import date

st.set_page_config(page_title="AMC NTEP Master Dashboard", layout="wide")

# --- 1. LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.title("AMC NTEP Login")
    pwd = st.text_input("Password", type="password")
    if st.button("Login"):
        if pwd == "AMC@2026": st.session_state.auth = True; st.rerun()
        else: st.error("Wrong Password")
    st.stop()

# --- 2. RAW EXCEL GRID HELPERS ---
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

# --- 3. THE EXCEL MIMIC ENGINE ---
@st.cache_data
def process_data():
    files = glob.glob("data/*.xlsx")
    df_slpa, df_udst, df_npo, df_op, df_cp = [pd.DataFrame()] * 5
    df_adt, df_rbs, df_art, df_cpt, df_hiv = [pd.DataFrame()] * 5
    diagnostics = []
    
    df_z = pd.DataFrame()
    for f in files:
        if "zone" in f.lower() and "~$" not in f:
            try:
                df_z = pd.read_excel(f, usecols=[0,1])
                df_z.columns = ['PHI_Map', 'Zone_Map']
                df_z['PHI_Map'] = df_z['PHI_Map'].astype(str).str.strip().str.upper()
                diagnostics.append("Zone Map Loaded")
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
                'Episode ID': filtered_df['Standard_ID'],
                'Patient Name': get_col(filtered_df, name_let),
                'TB Unit': get_col(filtered_df, tu_let),
                'PHI': get_col(filtered_df, phi_let),
                'Facility Type': get_col(filtered_df, type_let),
                'Diagnosis Date': get_col(filtered_df, diag_let),
                'Initiation Date': get_col(filtered_df, init_let),
                'Outcome Date': get_col(filtered_df, out_let)
            })
            
            clean_df['merge_key'] = clean_df['PHI'].astype(str).str.strip().str.upper()
            if not df_z.empty:
                merged = clean_df.merge(df_z, left_on='merge_key', right_on='PHI_Map', how='left')
                merged['ZONE'] = merged['Zone_Map'].fillna("Zone Not Found")
            else:
                merged = clean_df.assign(ZONE="No Zone File")
                
            return merged[base_cols]

        if file_type == "LAB":
            site_c = get_col(df, 'F').str.lower()
            is_pulm = site_c.str.contains("pulmonary", na=False) & ~site_c.str.contains("extra", na=False)
            
            is_udst = is_pulm & is_blank(get_col(df, 'AQ')) & is_blank(get_col(df, 'AU')) & is_blank(get_col(df, 'BC'))
            df_udst = finalize_df(df[is_udst], 'T', 'V', 'P', 'Q', 'R', 'A', 'B', 'AF')

            has_rif = get_col(df, 'AR').str.lower().str.contains("rif resistance detected", na=False) | \
                      get_col(df, 'AZ').str.lower().str.contains("rif resistance detected", na=False) | \
                      get_col(df, 'BD').str.lower().str.contains("rif resistance detected", na=False)
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

    return tuple(all_raw_dfs), diagnostics

(f_slpa, f_udst, f_npo, f_op, f_cp, f_adt, f_rbs, f_art, f_cpt, f_hiv), diag_logs = process_data()

master_reports = {
    "SLPA Pending": {"df": f_slpa, "icon": "🔴"}, "UDST Pending": {"df": f_udst, "icon": "🟡"},
    "Not Put On": {"df": f_npo, "icon": "⚪"}, "Outcome Pending": {"df": f_op, "icon": "🟢"},
    "Consent Pending": {"df": f_cp, "icon": "🟣"}, "ADT Pending": {"df": f_adt, "icon": "🩸"},
    "RBS Pending": {"df": f_rbs, "icon": "💉"}, "ART Pending": {"df": f_art, "icon": "💊"},
    "CPT Pending": {"df": f_cpt, "icon": "🛡️"}, "HIV Pending": {"df": f_hiv, "icon": "🔬"}
}

# --- 4. BUILD THE MASTER PATIENT DATAFRAME ---
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
else:
    df_master = pd.DataFrame(columns=['Episode ID', 'Patient Name', 'ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Pending Status'])

# Reordered columns to flow logically from Macro to Micro
df_master = df_master[['ZONE', 'TB Unit', 'Facility Type', 'PHI', 'Patient Name', 'Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Pending Status']]

# --- 5. CORPORATE UI & CASCADING FILTERS ---
st.title("Ahmedabad Municipal Corporation")
st.subheader("NTEP Master Pendency Action List")

def get_opts(df, col):
    if df.empty or col not in df.columns: return []
    return sorted([str(x) for x in df[col].unique() if str(x).strip() not in ["", "nan", "None", "Zone Not Found", "N/A"]])

# Clean, professional container box
with st.container(border=True):
    st.markdown("#### Data Control Center")
    
    f_rep = st.multiselect("Report Type", list(master_reports.keys()), placeholder="Select specific reports (leave blank for all)")
    
    st.markdown("##### Organizational Filters")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # 1. Zone
        sel_zone = st.multiselect("Zone", get_opts(df_master, 'ZONE'))
        df_for_tu = df_master[df_master['ZONE'].isin(sel_zone)] if sel_zone else df_master
        
    with col2:
        # 2. TB Unit depends on Zone
        sel_tu = st.multiselect("TB Unit", get_opts(df_for_tu, 'TB Unit'))
        df_for_type = df_for_tu[df_for_tu['TB Unit'].isin(sel_tu)] if sel_tu else df_for_tu
        
    with col3:
        # 3. Facility Type depends on TB Unit
        sel_type = st.multiselect("Facility Type", get_opts(df_for_type, 'Facility Type'))
        df_for_phi = df_for_type[df_for_type['Facility Type'].isin(sel_type)] if sel_type else df_for_type
        
    with col4:
        # 4. PHI depends on Facility Type
        sel_phi = st.multiselect("PHI", get_opts(df_for_phi, 'PHI'))

    st.markdown("##### Date Filters")
    d1, d2, d3, d4 = st.columns([1,1,1,0.5])
    with d1: dr_diag = st.date_input("Diagnosis Date", value=[], key="d1")
    with d2: dr_init = st.date_input("Initiation Date", value=[], key="d2")
    with d3: dr_out = st.date_input("Outcome Date", value=[], key="d3")
    with d4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Reset Dates", use_container_width=True): st.rerun()

# --- 6. APPLY FILTERS ---
df_display = df_master.copy()

if not df_display.empty:
    if sel_zone: df_display = df_display[df_display['ZONE'].isin(sel_zone)]
    if sel_tu: df_display = df_display[df_display['TB Unit'].isin(sel_tu)]
    if sel_type: df_display = df_display[df_display['Facility Type'].isin(sel_type)]
    if sel_phi: df_display = df_display[df_display['PHI'].isin(sel_phi)]
    
    if len(f_rep) > 0:
        pattern = "|".join(f_rep)
        df_display = df_display[df_display['Pending Status'].str.contains(pattern, regex=True, na=False)]
    
    if len(dr_diag) == 2:
        mask = (df_display['Diagnosis Date'].dt.date >= dr_diag[0]) & (df_display['Diagnosis Date'].dt.date <= dr_diag[1])
        df_display = df_display[mask | df_display['Diagnosis Date'].isna()]
        
    if len(dr_init) == 2:
        mask = (df_display['Initiation Date'].dt.date >= dr_init[0]) & (df_display['Initiation Date'].dt.date <= dr_init[1])
        df_display = df_display[mask | df_display['Initiation Date'].isna()]
        
    if len(dr_out) == 2:
        mask = (df_display['Outcome Date'].dt.date >= dr_out[0]) & (df_display['Outcome Date'].dt.date <= dr_out[1])
        df_display = df_display[mask | df_display['Outcome Date'].isna()]

filtered_counts = {}
for rep_name in master_reports.keys():
    if not df_display.empty:
        filtered_counts[rep_name] = len(df_display[df_display['Pending Status'].str.contains(rep_name, regex=False, na=False)])
    else:
        filtered_counts[rep_name] = 0

# --- 7. DYNAMIC DASHBOARD DISPLAY ---
total_unique_patients = len(df_display)
total_pendencies = sum(filtered_counts.values())

st.markdown("### Program Overview")
c_tot1, c_tot2 = st.columns(2)
with c_tot1: st.metric("Total Unique Patients", total_unique_patients)
with c_tot2: st.metric("Total Pendencies", total_pendencies)

st.markdown("### Pendency Indicators")
m1, m2, m3, m4, m5 = st.columns(5)
m6, m7, m8, m9, m10 = st.columns(5)

kpi_cols = [m1, m2, m3, m4, m5, m6, m7, m8, m9, m10]
for i, rep_name in enumerate(master_reports.keys()):
    # Kept the colored circles on the metrics just for fast visual distinction
    icon = master_reports[rep_name]["icon"]
    kpi_cols[i].metric(f"{icon} {rep_name.replace(' Pending', '')}", filtered_counts[rep_name])

st.divider()

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

col_title, col_btn = st.columns([3, 1])
with col_title:
    st.markdown("### Master Patient Action List")
with col_btn:
    st.download_button(
        label="Download Report (CSV)",
        data=convert_df(df_display),
        file_name="NTEP_Master_Action_List.csv",
        mime="text/csv",
        use_container_width=True
    )

conf = {
    "Diagnosis Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
    "Initiation Date": st.column_config.DateColumn(format="YYYY-MM-DD"),
    "Outcome Date": st.column_config.DateColumn(format="YYYY-MM-DD")
}
st.dataframe(df_display, use_container_width=True, hide_index=True, column_config=conf)

with st.expander("System Diagnostics"):
    for log in diag_logs: st.write(log)