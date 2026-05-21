"""
Configuration settings for Momence scraper.
Enhanced with v4.0 stability improvements.

RSO Phase 0 note (2026-05-21):
  This file has been relocated to services/momence/ in Ritual_Studio_Ops.
  The original Momence_data folder remains the live data directory.
  All data-file paths now resolve via MOMENCE_DATA_DIR so this code can live
  anywhere while still reading from and writing to the correct OneDrive location.

  Set MOMENCE_DATA_DIR in .env (or as an environment variable) to:
    C:\\Users\\markj\\OneDrive - MFPL\\Documents\\Customer Projects\\Ritual\\Momence_data
  If the variable is absent, paths fall back to the directory of this file
  (preserving backwards compatibility when running from the original location).
"""

import os as _os

# Code directory (where this config.py lives).
_CODE_DIR = _os.path.dirname(_os.path.abspath(__file__))

# Data directory — where master CSVs, cookies, checkpoints, logs live.
# Reads MOMENCE_DATA_DIR from .env or environment; falls back to the original
# Momence_data folder location so the existing daily chain is unaffected.
_DATA_DIR = _os.environ.get(
    'MOMENCE_DATA_DIR',
    _CODE_DIR  # fallback: same dir as code (original behaviour)
)

# URLs
BASE_URL = "https://momence.com"
DASHBOARD_URL = "https://momence.com/dashboard/32083"
LOGIN_URL = "https://momence.com/login"

# File paths — all resolve relative to _DATA_DIR so they always point at the
# live OneDrive data folder regardless of where this config.py is installed.
LOG_FILE        = _os.path.join(_DATA_DIR, 'Log_files', 'Momence_customer_log.txt')

# Master batch log location — moved out of OneDrive on 2026-05-18 to stop sync
# locks truncating writes mid-line. Falls back to the legacy in-tree location
# if the local-only folder is missing (e.g. clean checkout on a new machine).
_LOCAL_BATCH_LOG_DIR = r'C:\Users\markj\Momence_local_logs'
if _os.path.isdir(_LOCAL_BATCH_LOG_DIR):
    BATCH_LOG_FILE = _os.path.join(_LOCAL_BATCH_LOG_DIR, 'Momence_batch_log.txt')
else:
    BATCH_LOG_FILE = _os.path.join(_DATA_DIR, 'Log_files', 'Momence_batch_log.txt')

CHECKPOINT_FILE = _os.path.join(_DATA_DIR, 'scraper_checkpoint.json')
COOKIES_FILE    = _os.path.join(_DATA_DIR, 'momence_cookies.pkl')

# Performance and timing settings
STATUS_INTERVAL = 300     # Status report every 5 minutes (in seconds)
HEARTBEAT_INTERVAL = 300  # Heartbeat every 5 minutes (in seconds)
PING_TIMEOUT = 5         # Network check timeout in seconds

# Browser management
MAX_MEMORY_PERCENT = 80   # Restart browser if memory exceeds this percentage
CACHE_CLEAR_INTERVAL = 10 # Clear browser cache every N classes

# Error handling and retries
MAX_RETRIES = 3
RETRY_DELAYS = [5, 10, 20]  # Exponential backoff delays in seconds

# Request throttling
MIN_REQUEST_DELAY = 1.0  # Minimum delay between requests in seconds
MAX_REQUEST_DELAY = 5.0  # Maximum delay for heavy load conditions

# Element stability settings
ELEMENT_WAIT_TIMEOUT = 40  # Maximum time to wait for elements in seconds
PAGE_LOAD_TIMEOUT = 60    # Maximum time to wait for page load in seconds