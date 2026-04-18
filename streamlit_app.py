import streamlit as st
import pandas as pd
import glob
import os
from datetime import date
import base64

st.set_page_config(page_title="AMC NTEP Master Dashboard", layout="wide", initial_sidebar_state="collapsed")

# --- CUSTOM CSS ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 900px; }
    .amc-footer { text-align: center; font-size: 11px; color: #555; margin-top: 30px; padding-top: 15px; border-top: 1px solid #ddd; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# --- 1. LOGIN ---
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center; color: #1f618d; margin-top: 50px;'>🏥 AMC NTEP Login</h2>", unsafe_allow_html=True)
    pwd = st.text_input("Password", type="password")
    if st.button("Login", use_container_width=True):
        if pwd == "AMC@2026": st.session_state.auth = True; st.rerun()
        else: st.error("Wrong Password")
    st.stop()

# --- HELPERS ---
def img_to_b64(img_path):
    try:
        with open(img_path, "rb") as img_file: return base64.b64encode(img_file.read()).decode('utf-8')
    except: return ""

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

def get_opts(df, col):
    if df.empty or col not in df.columns: return []
    return sorted([str(x) for x in df[col].unique() if str(x).strip() not in ["", "nan", "None", "Zone Not Found", "N/A"]])

def draw_card(title, value, color, icon):
    return f"""
    <div style="background-color: {color}; border-radius: 8px; padding: 15px 5px; margin-bottom: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <div style="font-size: 24px; margin-bottom: 5px;">{icon}</div>
        <div style="font-size: 13px; font-weight: bold; text-transform: uppercase; line-height: 1.1;">{title}</div>
        <div style="font-size: 26px; font-weight: 900; margin-top: 8px;">{value}</div>
    </div>
    """

# --- 3. DATA ENGINE ---
@st.cache_data
def process_data():
    files = glob.glob("data/*.xlsx")
    df_slpa, df_udst, df_npo, df_op, df_cp = [pd.DataFrame()] * 5
    df_adt, df_rbs, df_art, df_cpt, df_hiv = [pd.DataFrame()] * 5
    
    extended_ids = set() 
    today_ts = pd.Timestamp(date.today())
    
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

        id_let = {'LAB': 'T', 'NOTIF': 'M', 'CONSENT': 'I', 'COMORB': 'K'}[file_type]
        df['Standard_ID'] = get_col(df, id_let).astype(str).str.strip().str.upper()
        df = df[~is_blank(df['Standard_ID'])].drop_duplicates(subset=['Standard_ID'], keep='last')

        base_cols = ['ZONE', 'TB Unit', 'Facility Type', 'PHI', 'Patient Name', 'Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Treatment Outcome']
        
        def finalize_df(filtered_df, id_let, name_let, tu_let, phi_let, type_let, diag_let, init_let, out_let, tr_out_let=None):
            if filtered_df.empty: return pd.DataFrame(columns=base_cols)
            return pd.DataFrame({
                'Episode ID': filtered_df['Standard_ID'], 'Patient Name': get_col(filtered_df, name_let),
                'TB Unit': get_col(filtered_df, tu_let), 'PHI': get_col(filtered_df, phi_let),
                'Facility Type': get_col(filtered_df, type_let), 'Diagnosis Date': get_col(filtered_df, diag_let),
                'Initiation Date': get_col(filtered_df, init_let), 'Outcome Date': get_col(filtered_df, out_let),
                'Treatment Outcome': get_col(filtered_df, tr_out_let) if tr_out_let else ""
            })

        if file_type == "LAB":
            site_c = get_col(df, 'F').str.lower()
            is_pulm = site_c.str.contains("pulmonary", na=False) & ~site_c.str.contains("extra", na=False)
            is_udst = is_pulm & is_blank(get_col(df, 'AQ')) & is_blank(get_col(df, 'AU')) & is_blank(get_col(df, 'BC'))
            df_udst = finalize_df(df[is_udst], 'T', 'V', 'P', 'Q', 'R', 'A', 'B', 'AF', 'AE')
            has_rif = get_col(df, 'AR').str.lower().str.contains("rif resistance", na=False) | get_col(df, 'BD').str.lower().str.contains("rif resistance", na=False)
            is_slpa = is_pulm & (has_rif | get_col(df, 'DO').str.lower().str.contains("inh resistance", na=False)) & is_blank(get_col(df, 'BH'))
            df_slpa = finalize_df(df[is_slpa], 'T', 'V', 'P', 'Q', 'R', 'A', 'B', 'AF', 'AE')

        elif file_type == "NOTIF":
            out_c, init_c = get_col(df, 'BK'), get_col(df, 'BM')
            out_date_c = pd.to_datetime(get_col(df, 'CB'), errors='coerce', dayfirst=True)
            init_date_c = pd.to_datetime(get_col(df, 'BM'), errors='coerce', dayfirst=True)
            reg_c = pd.Series([""] * len(df))
            for col in df.columns:
                if "regimen" in str(col).lower(): reg_c = df[col].astype(str).str.upper().str.replace(" ", ""); break
            
            df_npo = finalize_df(df[is_blank(init_c) & is_blank(out_c)], 'M', 'N', 'C', 'E', 'D', 'S', 'BM', 'CB', 'BK')
            
            # --- 1318 Outcome Pending ---
            df_op = finalize_df(df[is_blank(out_c) & (reg_c == "2HRZE/4HRE") & (out_date_c <= today_ts)], 'M', 'N', 'C', 'E', 'D', 'S', 'BM', 'CB', 'BK')

            # --- Extended Logic ---
            is_ext = is_blank(out_c) & (reg_c == "2HRZE/4HRE") & ((out_date_c - init_date_c).dt.days > 168)
            extended_ids.update(get_col(df[is_ext], 'M').astype(str).str.strip().str.upper().tolist())

        elif file_type == "CONSENT":
            df_cp = finalize_df(df[is_blank(get_col(df, 'Y'))], 'I', 'J', 'V', 'W', 'X', 'G', None, None, None)

        elif file_type == "COMORB":
            am, an, ah = get_col(df, 'AM').str.strip().str.lower(), get_col(df, 'AN').str.strip(), get_col(df, 'AH').str.strip().str.lower()
            al, ak, ai = get_col(df, 'AL').str.strip(), get_col(df, 'AK').str.strip(), get_col(df, 'AI').str.strip()
            is_hiv_reactive = ah.isin(["reactive", "positive"])
            df_adt = finalize_df(df[(am == "diabetic") & is_blank(an)], 'K', 'O', 'C', 'D', None, 'M', 'W', None, 'U')
            df_rbs = finalize_df(df[am.isin(["unknown", ""]) | is_blank(am)], 'K', 'O', 'C', 'D', None, 'M', 'W', None, 'U')
            df_art = finalize_df(df[is_hiv_reactive & is_blank(al)], 'K', 'O', 'C', 'D', None, 'M', 'W', None, 'U')
            df_cpt = finalize_df(df[is_hiv_reactive & is_blank(ak)], 'K', 'O', 'C', 'D', None, 'M', 'W', None, 'U')
            df_hiv = finalize_df(df[is_blank(ai)], 'K', 'O', 'C', 'D', None, 'M', 'W', None, 'U')

    all_raw = {"SLPA": df_slpa, "UDST": df_udst, "Not Put On": df_npo, "Outcome": df_op, "Consent": df_cp, "ADT": df_adt, "RBS": df_rbs, "ART": df_art, "CPT": df_cpt, "HIV": df_hiv}
    
    res_final = {}
    for name, d in all_raw.items():
        if d.empty: 
            res_final[name] = pd.DataFrame(columns=base_cols)
            continue
        d['merge_key'] = d['PHI'].astype(str).str.strip().str.upper()
        if not df_z.empty:
            merged = d.merge(df_z, left_on='merge_key', right_on='PHI_Map', how='left')
            merged['ZONE'] = merged['Zone_Map'].fillna("Zone Not Found")
        else: merged = d.assign(ZONE="No Zone File")
        res_final[name] = merged[base_cols]

    return res_final, extended_ids

reps_dict, extended_ids = process_data()

pieces = []
for name, d in reps_dict.items():
    if not d.empty:
        temp = d.copy()
        temp['Pending Status'] = name
        pieces.append(temp)

if pieces:
    all_p = pd.concat(pieces)
    df_master = all_p.groupby('Episode ID').agg({
        'Patient Name': 'first', 'ZONE': 'first', 'TB Unit': 'first', 'PHI': 'first',
        'Facility Type': 'first', 'Diagnosis Date': 'first', 'Initiation Date': 'first', 'Outcome Date': 'first',
        'Treatment Outcome': 'first', 'Pending Status': lambda x: " + ".join(x.unique())
    }).reset_index()
    df_master['Extend Status'] = df_master['Episode ID'].apply(lambda x: "Extended" if x in extended_ids else "")
else:
    df_master = pd.DataFrame(columns=['Episode ID', 'Patient Name', 'ZONE', 'TB Unit', 'PHI', 'Facility Type', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Treatment Outcome', 'Extend Status', 'Pending Status'])

# --- REORDER COLUMNS (Extend Status 2nd to last, Pending Status last) ---
cols_ordered = ['ZONE', 'TB Unit', 'Facility Type', 'PHI', 'Patient Name', 'Episode ID', 'Diagnosis Date', 'Initiation Date', 'Outcome Date', 'Treatment Outcome', 'Extend Status', 'Pending Status']
df_master = df_master[cols_ordered]

# --- UI ---
b64_amc, b64_ntep, b64_h1, b64_h2 = img_to_b64("images/amc.png"), img_to_b64("images/ntep.jpg"), img_to_b64("images/h1.jpg"), img_to_b64("images/h2.jpg")
src_amc, src_ntep, src_h1, src_h2 = f"data:image/png;base64,{b64_amc}", f"data:image/jpeg;base64,{b64_ntep}", f"data:image/jpeg;base64,{b64_h1}", f"data:image/jpeg;base64,{b64_h2}"

st.markdown(f"<div style='display: flex; justify-content: space-between; align-items: center;'><img src='{src_amc}' height='75'><h3 style='margin:0; font-weight:900;'>AMC | NTEP</h3><img src='{src_ntep}' height='75'></div>", unsafe_allow_html=True)
st.markdown("<div style='background-color:#1f618d; color:white; text-align:center; padding:12px; border-radius:5px; margin:15px 0;'>TB Monitoring Dashboard - Ahmedabad</div>", unsafe_allow_html=True)
st.markdown(f"<div style='display:flex; gap:8px; margin-bottom: 20px;'><img src='{src_h1}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'><img src='{src_h2}' style='width:50%; height:130px; object-fit:cover; border-radius:5px;'></div>", unsafe_allow_html=True)

# --- FILTERS ---
with st.expander("🔽 Filters & Sorting"):
    f_rep = st.multiselect("Report Type", list(reps_dict.keys()), placeholder="All Reports")
    c1, c2 = st.columns(2)
    with c1:
        s_z = st.multiselect("Zone", get_opts(df_master, 'ZONE'))
        df_for_tu = df_master[df_master['ZONE'].isin(s_z)] if s_z else df_master
        s_tu = st.multiselect("TB Unit", get_opts(df_for_tu, 'TB Unit'))
    with c2:
        df_for_type = df_for_tu[df_for_tu['TB Unit'].isin(s_tu)] if s_tu else df_for_tu
        s_ft = st.multiselect("Facility Type", get_opts(df_for_type, 'Facility Type'))
        df_for_phi = df_for_type[df_for_type['Facility Type'].isin(s_ft)] if s_ft else df_for_type
        s_phi = st.multiselect("PHI", get_opts(df_for_phi, 'PHI'))
    
    st.markdown("---")
    d1, d2, d3 = st.columns(3)
    with d1: dr_diag = st.date_input("Diagnosis Date Filter", value=[], key="dr1")
    with d2: dr_init = st.date_input("Initiation Date Filter", value=[], key="dr2")
    with d3: dr_out = st.date_input("Outcome Date Filter", value=[], key="dr3")
    if st.button("Reset Filters", use_container_width=True): st.rerun()

df_display = df_master.copy()
if s_z: df_display = df_display[df_display['ZONE'].isin(s_z)]
if s_tu: df_display = df_display[df_display['TB Unit'].isin(s_tu)]
if s_ft: df_display = df_display[df_display['Facility Type'].isin(s_ft)]
if s_phi: df_display = df_display[df_display['PHI'].isin(s_phi)]
if f_rep: df_display = df_display[df_display['Pending Status'].str.contains("|".join(f_rep), na=False)]

for col, dr in [('Diagnosis Date', dr_diag), ('Initiation Date', dr_init), ('Outcome Date', dr_out)]:
    if len(dr) == 2:
        df_display[col] = pd.to_datetime(df_display[col], errors='coerce')
        df_display = df_display[(df_display[col].dt.date >= dr[0]) & (df_display[col].dt.date <= dr[1])]

f_counts = {k: len(df_display[df_display['Pending Status'].str.contains(k, na=False)]) for k in reps_dict.keys()}

c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(draw_card("Total Pending Patients", len(df_display), "#1f618d", "👥"), unsafe_allow_html=True)
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
if sq: df_display = df_display[df_display['Patient Name'].str.contains(sq, case=False, na=False) | df_display['Episode ID'].str.contains(sq, case=False, na=False)]

conf = {"Diagnosis Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Initiation Date": st.column_config.DateColumn(format="DD-MM-YYYY"), "Outcome Date": st.column_config.DateColumn(format="DD-MM-YYYY")}
st.dataframe(df_display, use_container_width=True, hide_index=True, column_config=conf, height=400)

st.download_button("📥 Download Data (CSV)", df_display.to_csv(index=False).encode('utf-8'), "NTEP_Data.csv", "text/csv", use_container_width=True)
st.markdown("<div class='amc-footer'>Created by District TB Center AMC | NTEP Monitoring System</div>", unsafe_allow_html=True)
