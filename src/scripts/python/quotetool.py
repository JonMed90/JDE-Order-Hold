# Load and inspect the uploaded Excel, then reshape to a lookup-friendly table.
import pandas as pd
from pathlib import Path

src = Path(r"C:\Users\JMedina\OneDrive - Stryker\Desktop\ApproverAlignment.xlsx")
xl = pd.ExcelFile(src)


# Prefer the first sheet
df = xl.parse(xl.sheet_names[0])

# Trim whitespace in column headers
df.columns = [str(c).strip() for c in df.columns]

# Identify likely ERP ID and Account Name columns by simple heuristics
id_cols = [c for c in df.columns if "Ship-To" in c or "Account #" in c or "Account#" in c]
name_cols = [c for c in df.columns if "Account Name" in c]

# Keep KAE if present
extra_cols = [c for c in df.columns if c.strip().upper() == "KAE"]
extra_cols += [c for c in df.columns if c in ["FA Region","TR Region","UE Region","JR Region","FA RSM","TR RSM","UE RSM","JR RSM"]]

# Build a mapping between each ID column and its matching Account Name column based on prefix
pairs = []
for idc in id_cols:
    base = idc.replace("Ship-To","").replace("Account #","").replace("Account#","").strip()
    # find best matching account name col containing same base
    cand = [nc for nc in name_cols if base and base in nc]
    # fallback to exact knowns
    if not cand:
        if "JDE 9.0" in idc:
            cand = [c for c in name_cols if "JDE 9.0" in c]
        elif "JDE 9.1" in idc:
            cand = [c for c in name_cols if "JDE 9.1" in c]
        elif "Model N" in idc:
            cand = [c for c in name_cols if "Model N" in c]
    if cand:
        pairs.append((idc, cand[0]))
        
# Reshape to long format for each ERP-ID pair
long_frames = []
for idc, namec in pairs:
    erp = idc.replace("Ship-To","").replace("Account #","").replace("Account#","").strip()
    subcols = [idc, namec] + [c for c in extra_cols if c in df.columns]
    tmp = df[subcols].copy()
    tmp.rename(columns={idc:"ERP_ID", namec:"AccountName"}, inplace=True)
    tmp.insert(0, "ERPKey", idc)      # e.g., "JDE 9.0 Ship-To"
    tmp.insert(1, "ERPSystem", erp)   # e.g., "JDE 9.0"
    long_frames.append(tmp)

if long_frames:
    lookup = pd.concat(long_frames, ignore_index=True)
else:
    lookup = pd.DataFrame(columns=["ERPKey","ERPSystem","ERP_ID","AccountName"] + extra_cols)

# Clean values
for col in ["ERP_ID","AccountName"]:
    if col in lookup.columns:
        lookup[col] = lookup[col].astype(str).str.strip().replace("nan", pd.NA)

# Drop rows where ERP_ID is blank or null
lookup = lookup[lookup["ERP_ID"].notna() & (lookup["ERP_ID"].astype(str).str.len() > 0)]

# Deduplicate
keep_cols = [c for c in ["ERPKey","ERPSystem","ERP_ID","AccountName","KAE","FA Region","TR Region","UE Region","JR Region","FA RSM","TR RSM","UE RSM","JR RSM"] if c in lookup.columns]
lookup = lookup[keep_cols].drop_duplicates()

# Save outputs to current directory
out_csv = Path("ApproverAlignment_Lookup.csv")
out_xlsx = Path("ApproverAlignment_Lookup.xlsx")
lookup.to_csv(out_csv, index=False)
lookup.to_excel(out_xlsx, index=False)

# Show a small preview
print(lookup.head(25))
