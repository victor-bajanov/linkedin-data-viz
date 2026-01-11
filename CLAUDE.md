# Project: LinkedIn Data Visualization Dashboard

A Dash-based web app for visualizing LinkedIn connection data with CRM-like features.

## Architecture

### Key Files
- `app.py` - Main Dash application, tab creation, callbacks
- `shortlist_viewer.py` - CRM tab logic, shortlist management functions
- `data_loader.py` - LinkedIn CSV data loading

### Data Storage
- `connections_shortlist.json` - Active shortlist with contact info + CRM fields (status, comments, last_updated)
- `crm_archive.json` - Archived CRM data keyed by contact name (preserves data for removed contacts)

### Data Flow: Shortlist Modification
When user selects/deselects contacts in Connections tab:
1. `update_shortlist()` in `app.py` is triggered
2. It loads the **current shortlist first** to preserve existing CRM data
3. Falls back to `crm_archive.json` only for contacts being re-added after removal
4. Saves merged result to `connections_shortlist.json`

This two-tier approach ensures CRM work isn't lost when modifying the shortlist.

### CRM Data Persistence
When saving CRM changes (status/comments):
1. Updates `connections_shortlist.json` (active list)
2. Also saves to `crm_archive.json` (backup for remove/re-add scenarios)

## Running
```bash
source .venv/bin/activate
python app.py
```
App runs on http://localhost:8050
