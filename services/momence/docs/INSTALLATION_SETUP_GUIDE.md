# RITUAL ANALYSIS SCRIPTS - INSTALLATION & SETUP GUIDE

**Created:** 2025-02-01  
**Purpose:** Complete setup instructions for running Momence data analysis scripts

---

## PREREQUISITES

### 1. Python Installation
- **Version:** Python 3.8 or higher recommended
- **Check:** Open Command Prompt and run: `python --version`

### 2. Required Python Packages

Run these commands in Command Prompt (cmd) or PowerShell:

```bash
# Core data analysis packages
pip install pandas
pip install openpyxl
pip install xlsxwriter

# API and HTTP handling
pip install requests
pip install python-dotenv
```

**Verification:**
```bash
python -c "import pandas, openpyxl, xlsxwriter, requests; print('All packages installed successfully')"
```

---

## COMMON INSTALLATION ISSUES & FIXES

### Issue 1: ModuleNotFoundError: No module named 'xlsxwriter'

**Error Message:**
```
ModuleNotFoundError: No module named 'xlsxwriter'
```

**Solution:**
```bash
pip install xlsxwriter
```

### Issue 2: None values causing arithmetic errors

**Error Message:**
```
TypeError: unsupported operand type(s) for -: 'NoneType' and 'int'
```

**Fix Applied:** All scripts updated to handle None values:
```python
# WRONG (causes error with None):
capacity = s.get('capacity', 0)

# CORRECT (handles None properly):
capacity = s.get('capacity') or 0
```

### Issue 3: Timezone-aware datetime in Excel

**Error Message:**
```
ValueError: Excel does not support datetimes with timezones
```

**Fix Applied:** All scripts now remove timezone info:
```python
df['starts_at'] = pd.to_datetime(df['starts_at']).dt.tz_localize(None)
```

### Issue 4: Division by zero

**Error Message:**
```
ZeroDivisionError: division by zero
# or
RuntimeWarning: divide by zero encountered
```

**Fix Applied:** All fill rate calculations now check for zero capacity:
```python
# WRONG (can divide by zero):
fill_rate = (bookings / capacity * 100)

# CORRECT (handles zero capacity):
fill_rate = (bookings / capacity * 100) if capacity > 0 else 0
```

---

## DIRECTORY STRUCTURE

Ensure your directories are set up correctly:

```
C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\
├── Momence_data\
│   ├── .env                          # API credentials (MUST exist)
│   ├── momence_api_client.py         # API client (MUST exist)
│   ├── step1_sample_analysis.py      # New script - Sample analysis
│   ├── step2_full_analysis.py        # New script - Full dataset
│   └── step3_kpi_dashboard.py        # New script - KPI dashboard
└── [Output files will be created here]
```

---

## CREDENTIALS CHECK

Your `.env` file MUST contain all 5 credentials:

**Location:** `C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\.env`

**Required Contents:**
```
MOMENCE_CLIENT_ID=api-32083-t5PW3f5B2k7plzue
MOMENCE_CLIENT_SECRET=miZi44HVizs0eLU5FTOvXRPeslg0fxzj
MOMENCE_USERNAME=markjfellows@hotmail.com
MOMENCE_PASSWORD=Momence2007
MOMENCE_HOST_ID=32083
```

**Verification:**
```python
python -c "from pathlib import Path; from dotenv import load_dotenv; import os; load_dotenv(Path(r'C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data\.env')); print('✓ Client ID:', os.getenv('MOMENCE_CLIENT_ID')[:15] + '...'); print('✓ Host ID:', os.getenv('MOMENCE_HOST_ID'))"
```

---

## RUNNING THE SCRIPTS

### Step 1: Sample Analysis (RECOMMENDED FIRST)

**Purpose:** Test with 1,000 sessions (~2 minutes)

```bash
cd "C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
python step1_sample_analysis.py
```

**Output:** `Ritual_2025_Sample_Analysis.xlsx`

**What it contains:**
- Monthly Summary with trend chart
- Location Summary with bar chart
- Discipline Summary
- Day of Week patterns
- Raw session data

**Runtime:** ~2 minutes

---

### Step 2: Full Analysis (COMPREHENSIVE)

**Purpose:** Analyse ALL 55,000+ sessions

⚠️ **WARNING:**
- Takes 10-15 minutes
- Makes ~550 API calls
- Requires stable internet connection

```bash
cd "C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
python step2_full_analysis.py
```

**Output:** `Ritual_2025_FULL_Analysis.xlsx`

**What it contains:**
- Monthly Summary with comprehensive metrics
- Location Performance breakdown
- Discipline Performance analysis
- Location × Discipline cross-analysis
- Day of Week patterns
- Complete raw data (all sessions)

**Runtime:** ~10-15 minutes

---

### Step 3: KPI Dashboard (STRATEGIC)

**Purpose:** Generate KPIs from your proposal

```bash
cd "C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\Momence_data"
python step3_kpi_dashboard.py
```

**Output:** `Ritual_KPI_Dashboard.xlsx`

**What it contains:**
- Engagement KPIs (fill rates, waitlist analysis)
- Location Performance metrics
- Discipline Performance metrics
- Top 10 Teachers by fill rate
- Fitness Passport KPI structure (requires booking data)
- Peak vs Off-Peak analysis
- Day of Week patterns
- Session-level details

**Runtime:** ~5 minutes (last 3 months of data)

---

## ALL FIXES APPLIED TO SCRIPTS

### ✅ Fix 1: None Value Handling
```python
# Changed all instances of:
s.get('capacity', 0)          # WRONG
# To:
s.get('capacity') or 0        # CORRECT
```

### ✅ Fix 2: Timezone Removal
```python
# Added after datetime conversion:
df['starts_at'] = pd.to_datetime(df['starts_at']).dt.tz_localize(None)
```

### ✅ Fix 3: Division by Zero Protection
```python
# Changed all fill rate calculations:
monthly['fill_rate_%'] = monthly.apply(
    lambda row: round(row['bookings'] / row['capacity'] * 100, 1) if row['capacity'] > 0 else 0,
    axis=1
)
```

### ✅ Fix 4: None Location Handling
```python
# Added None checks:
location': loc.get('name') if isinstance(loc, dict) else str(loc) if loc else 'Unknown'
```

### ✅ Fix 5: Safe Statistics Output
```python
# Protected all division operations:
total_capacity = df['capacity'].sum()
if total_capacity > 0:
    print(f"Average fill rate: {(df['bookings'].sum() / total_capacity * 100):.1f}%")
else:
    print(f"Average fill rate: N/A (no capacity data)")
```

---

## EXPECTED OUTPUT FILES

After running all three scripts successfully:

```
C:\Users\markj\OneDrive - MFPL\Documents\Customer Projects\Ritual\
├── Ritual_2025_Sample_Analysis.xlsx      # From Step 1
├── Ritual_2025_FULL_Analysis.xlsx        # From Step 2
└── Ritual_KPI_Dashboard.xlsx             # From Step 3
```

---

## TROUBLESHOOTING

### Script won't start

**Check:**
1. Python installed? `python --version`
2. In correct directory? `cd` to Momence_data folder
3. Packages installed? Run pip install commands above
4. .env file exists? Check path

### Authentication fails

**Check:**
1. .env file location: Must be in Momence_data folder
2. All 5 credentials present
3. No extra spaces or quotes in .env file
4. Internet connection active

### Script stops partway through

**Possible causes:**
1. Internet disconnection - restart from beginning
2. API rate limit - script has built-in delays
3. Python crash - check error message

### Excel file won't open

**Check:**
1. File actually created? Look in output directory
2. Excel installed?
3. File not corrupted - check file size (>0 bytes)

### Wrong data in output

**Check:**
1. Using latest script versions (with all fixes)
2. Date ranges correct (2025 for current analysis)
3. API returning expected data

---

## PERFORMANCE TIPS

### For Faster Results:
1. Start with Step 1 (sample) - confirms everything works
2. Run Step 3 before Step 2 - gets KPIs faster
3. Close other applications during Step 2 (full analysis)

### For Better Data:
1. Run during off-peak hours (fewer API conflicts)
2. Ensure stable internet connection
3. Don't interrupt scripts mid-execution

---

## NEXT STEPS AFTER SUCCESSFUL RUNS

1. ✅ **Review Sample Analysis** (Step 1 output)
   - Confirm data looks correct
   - Check locations match: Palm Beach, Mermaid, Robina
   - Verify disciplines: Reformer, Mat Pilates, Barre, Yoga, Yin

2. ✅ **Run Full Analysis** (Step 2)
   - Get complete 2025 picture
   - Identify trends over all months
   - Spot high/low performing times

3. ✅ **Review KPI Dashboard** (Step 3)
   - Compare against proposal targets
   - Identify action items
   - Note data gaps (Fitness Passport, attendance rates)

4. 📋 **Next Phase** (requires additional work):
   - Fetch booking-level data for attendance rates
   - Identify Fitness Passport memberships
   - Calculate client retention metrics
   - Integrate Xero revenue data

---

## SUPPORT

If you encounter issues not covered here:

1. Check error message carefully
2. Verify all prerequisites installed
3. Confirm .env file is correct
4. Try Step 1 first (smallest test)
5. Reference the MOMENCE_SKILL_USAGE_GUIDE.md

---

**Last Updated:** 2025-02-01  
**Status:** All scripts tested and fixed  
**Python Version:** 3.8+  
**All Known Issues:** Resolved ✅
