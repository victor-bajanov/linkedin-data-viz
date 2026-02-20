# LinkedIn Data Dashboard

A comprehensive interactive dashboard for visualising and analysing your LinkedIn data export.

## Features

### 9 Interactive Tabs:

1. **Profile Overview** - Personal information, skills distribution, and professional summary
2. **Network Analytics** - Connection growth timeline, top companies in network, endorsements
3. **Career Journey** - Career timeline visualisation, education history, certifications
4. **Connections** - Interactive table of all LinkedIn connections with selection and shortlist management
5. **Communications** - Message volume analysis, top conversation partners
6. **Job Search** - Application trends, target companies, saved jobs statistics
7. **Learning** - Course activity, content type distribution, recent learning
8. **Financial** - LinkedIn Premium spending analysis and transaction history
9. **Shortlist CRM** - Full CRM pipeline for managing shortlisted contacts (see below)

### Shortlist CRM

The CRM tab provides a pipeline for tracking and managing shortlisted LinkedIn contacts:

- **12 pipeline statuses**: New, On Hold, To Contact, Contacted, Meeting Scheduled, In Conversation, Follow Up, Proposal Requested, Proposal Sent, Closed (Positive), Closed (Negative), Closed (Potential Referrer)
- **Keyboard shortcuts**: Number keys `1`-`9`, `0` for statuses; letter shortcuts (`c` Contacted, `h` On Hold, `x` To Contact, `t` In Conversation, `s` Meeting Scheduled, `f` Follow Up, `r` Proposal Requested, `p` Proposal Sent, `n` Closed Negative, `e` Closed Referrer); arrow keys for navigation; `Cmd+Z` / `Ctrl+Z` to undo the last status change
- **Follow-up dates**: Press `f` then enter a number of days (e.g. `f7`) to set a follow-up date; follow-up contacts are sorted soonest-first
- **Auto-save**: Status and follow-up date changes save instantly; comments are debounced and saved automatically
- **Right-click context menu**: Right-click any row to edit Company, Status, Follow-up Date, and Comments inline
- **Multi-select status filter**: Filter the CRM table by one or more statuses simultaneously
- **CRM data persistence**: Two-tier archive system — active data in `connections_shortlist.json`, backup in `crm_archive.json` so CRM data is preserved when contacts are removed and re-added to the shortlist

### LinkedIn Profile Import Bookmarklet

A browser bookmarklet (`utils/bookmarklet.js`) lets you import contacts directly from LinkedIn profile pages into the CRM:

1. Install the bookmarklet via `utils/bookmarklet_install.html`
2. Navigate to any LinkedIn profile and click the bookmarklet
3. It extracts the contact's name, position, company, and profile URL
4. Sends the data to the dashboard's `/api/import-contact` endpoint and adds them to your shortlist

## Installation

### Using pip:
```bash
# Install required packages
pip install -r requirements.txt
```

### Using uv (recommended):
```bash
# Install dependencies with uv
uv sync
```

## Usage

### Using pip:
```bash
# Run the dashboard
python app.py
```

### Using uv (recommended):
```bash
# Run the dashboard with uv
uv run python app.py
```

Then open your browser and navigate to: `http://localhost:8050`

## Data Structure

The dashboard expects LinkedIn data export CSV files in the following structure. This matches the format provided by LinkedIn's official data export feature:

```
data/
├── Profile.csv
├── Connections.csv
├── Positions.csv
├── Skills.csv
├── Education.csv
├── messages.csv
├── Jobs/
│   ├── Job Applications.csv
│   ├── Saved Jobs.csv
│   └── Job Seeker Preferences.csv
├── Learning.csv
├── Receipts_v2.csv
└── ... (other LinkedIn export files)
```

**Note**: Place all CSV files from your LinkedIn data export in the `data/` directory. The data export can be requested from LinkedIn's Privacy Settings under "Get a copy of your data".

## Key Insights Provided

- **Professional Growth**: Track career progression and role changes over time
- **Network Analysis**: Understand your professional network composition and growth
- **Skill Development**: Visualise skill endorsements and learning patterns
- **Job Search Patterns**: Analyse application trends and target companies
- **Communication Patterns**: Understand messaging frequency and key contacts
- **Investment in Learning**: Track LinkedIn Learning course engagement
- **Financial Overview**: Monitor LinkedIn Premium subscription costs
- **Connection Management**: View, filter, sort, and create shortlists of all LinkedIn connections with persistent JSON export
- **CRM Pipeline**: Track contact status through a full sales/networking pipeline with keyboard-driven workflow
- **Quick Import**: Add LinkedIn contacts to your CRM directly from their profile page via bookmarklet

## Customisation

The dashboard can be customised by modifying:
- `app.py` - Main application, tab layouts, and API endpoints
- `shortlist_viewer.py` - CRM tab logic, statuses, and keyboard shortcuts
- `data_loader.py` - Data processing and cleaning logic
- `assets/style.css` - Visual styling and themes
- `utils/bookmarklet.js` - LinkedIn profile import bookmarklet

## Requirements

- Python 3.8+
- Dash 2.14+
- Plotly 5.19+
- Pandas 2.1+