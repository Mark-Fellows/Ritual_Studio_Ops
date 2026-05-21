"""
ALL CLASSES WITH SIGNUPS EXTRACTOR - Business Overview
=======================================================
This script filters and extracts all fitness classes that have at least one customer 
signup (signups > 0). It processes the latest class data from the Momence system and 
identifies all classes with active bookings for further analysis.

Source Files: momence_classes_f_*.csv (latest file by modification date)

Output Files: 
1. momence_all_classes_[timestamp].csv - Dated snapshot of all classes with signups from this run
   (Note: The timestamp in the filename reflects the source data's collection time, 
   not when the extraction script ran, ensuring the output filename aligns with the 
   source data timestamp)
2. momence_fullclasses_log.csv - Cumulative log of all classes with signups over time

Output Field Names: (Preserves all fields from the source file, including)
- Class Number: Unique identifier for the class
- Class Name: Name/title of the class
- Schedule Time: When the class is scheduled
- Capacity: Maximum number of students for the class
- Signups: Current number of students signed up for the class
- (plus any additional fields from the source data)

Business Use Cases:
- Identify all classes with confirmed bookings for capacity management
- Track class popularity and engagement across the studio
- Build customer rosters for classes with active participation
- Generate class-level analytics and reporting
"""

import os
import glob
import csv
import re
import sys
import time
from datetime import datetime

# Batch log — absolute path relative to this script file so it is found
# regardless of the process working directory or Task Scheduler "Start In".
_SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
Batch_Log_file = os.path.join(_SCRIPT_DIR, 'Log_files', 'Momence_batch_log.txt')

def append_to_batch_log(message):
    """Append a timestamped message to the batch log file.

    Retries up to 3 times (2-second gap) to handle transient OneDrive locks.
    Falls back to stderr so the message appears in the chain log.
    """
    os.makedirs(os.path.dirname(Batch_Log_file), exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"{timestamp} - {message}\n"
    for attempt in range(3):
        try:
            with open(Batch_Log_file, 'a', encoding='utf-8') as batch_log:
                batch_log.write(line)
            return
        except Exception as exc:
            if attempt < 2:
                time.sleep(2)
            else:
                print(f"[BATCH LOG WRITE FAILED after 3 attempts: {exc}] {line.rstrip()}", file=sys.stderr)

files = glob.glob("momence_classes_f_*.csv")
if not files:
    print("No source files found!")
    exit(1)

latest_file = max(files, key=os.path.getmtime)
filename_only = os.path.basename(latest_file)
print(f"Using file: {latest_file}")

# 2. Derive a timestamp from the input filename or use current time
match = re.search(r'momence_classes_f_(\d{4} \d{2} \d{2} \d{2} \d{2})\.csv', filename_only)
if match:
    timestamp_str = match.group(1)
else:
    timestamp_str = datetime.now().strftime("%Y %m %d %H %M")

# 3. Output filenames
dated_output_file = f"momence_all_classes_{timestamp_str}.csv"
append_output_file = "Log_files/momence_fullclasses_log.csv"

# 4. Extract classes where signups > 0
matched_rows = []
headers = []

with open(latest_file, encoding='utf-8') as infile:
    reader = csv.DictReader(infile)
    headers = reader.fieldnames
    for row in reader:
        signups = row.get("Signups", "").replace("NA", "").strip()
        if signups.isdigit() and int(signups) > 0:
            matched_rows.append(row)

# 5. Write the dated output file (overwrite/replace each run)
with open(dated_output_file, "w", newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=headers)
    writer.writeheader()
    writer.writerows(matched_rows)

# 6. Append to the cumulative log file, writing header only if file doesn't exist yet
file_exists = os.path.isfile(append_output_file)
with open(append_output_file, "a", newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=headers)
    if not file_exists:
        writer.writeheader()
    writer.writerows(matched_rows)

extracted_count = len(matched_rows)
print(f"Extracted {extracted_count} classes with signups > 0 to {dated_output_file}")
print(f"Appended to {append_output_file}")

# Also append a short summary line to the shared batch log
append_to_batch_log(f"Extract all classes 1 ran, and extracted {extracted_count} classes with signups > 0")