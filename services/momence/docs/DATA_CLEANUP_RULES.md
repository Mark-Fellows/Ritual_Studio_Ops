# Data Cleanup Rules Applied to Master Files

**Date:** 2026-02-11

## Summary

Added automatic data cleaning rules that are applied every time the master files are updated.

## Rules Applied

### Failed Penalties Report
1. ✅ **Remove "Home location" column**
   - This column is removed from the master file
   - Original data in archive is preserved

### Late Cancellations Report
1. ✅ **Fill empty "Membership name" with "blank"**
   - Replaces both `NaN` and empty strings with "blank"
   - Makes data analysis easier (no null values)

2. ✅ **Fill empty "Penalty charged" with 0**
   - Replaces both `NaN` and empty strings with 0
   - Ensures numeric operations work correctly

3. ✅ **Remove "Home location" column**
   - This column is removed from the master file
   - Original data in archive is preserved

### No Shows Report
1. ✅ **Fill empty "Membership used" with "blank"**
   - Replaces both `NaN` and empty strings with "blank"
   - Makes data analysis easier (no null values)

2. ✅ **Fill empty "Penalty charged" with 0**
   - Replaces both `NaN` and empty strings with 0
   - Ensures numeric operations work correctly

3. ✅ **Remove "Home location" column**
   - This column is removed from the master file
   - Original data in archive is preserved

## Implementation

These rules are automatically applied in the processing functions:
- `append_and_dedupe_penalties()` - line ~800
- `append_and_dedupe_late_cancellations()` - line ~928
- `append_and_dedupe_no_shows()` - line ~1140

The cleanup happens **after deduplication** but **before saving** to ensure:
- All historical data is cleaned consistently
- Future downloads are automatically cleaned
- Original downloaded files in Archive are preserved unchanged

## Results of Initial Cleanup

Cleaned existing master files on 2026-02-11:

### Failed Penalties
- ✅ Removed "Home location" column

### Late Cancellations (173 records)
- ✅ Filled 15 empty "Membership name" values with "blank"
- ✅ Filled 109 empty "Penalty charged" values with 0
- ✅ Removed "Home location" column

### No Shows (32 records)
- ✅ Filled 9 empty "Membership used" values with "blank"
- ✅ Filled 20 empty "Penalty charged" values with 0
- ✅ Removed "Home location" column

## Final Column Structure

### Failed Penalties Master File
```
['Customer Name', 'Customer Email', 'Amount', 'Last fail',
 'Rerun count', 'Next rerun', 'Customer Number']
```

### Late Cancellations Master File
```
['Customer name', 'Customer Email', 'Cancelled Class', 'Cancelled Date',
 'Class Date', 'Paid', 'Payment Method', 'Membership name',
 'Penalty charged', 'Customer Number']
```

### No Shows Master File
```
['Customer Name', 'Customer Email', 'Class', 'Class Date', 'Teacher',
 'Payment Method', 'Membership used', 'Penalty charged',
 'Customer Number', 'Class Number']
```

## Benefits

1. ✅ **Consistent data** - No null values in key fields
2. ✅ **Easier analysis** - "blank" instead of empty makes filtering easier
3. ✅ **Numeric operations work** - 0 instead of empty for Penalty charged
4. ✅ **Cleaner exports** - No unnecessary location column
5. ✅ **Automatic** - Rules apply to all future downloads
6. ✅ **Preserved originals** - Archive folder keeps original downloads

## One-Time Cleanup Script

A one-time cleanup script was created and executed:
- **File:** `cleanup_existing_masters.py`
- **Purpose:** Apply rules to existing master files
- **Status:** Completed successfully

This script can be re-run if needed, or deleted if no longer required.
