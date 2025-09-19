# LinkedIn Data Dashboard

A comprehensive interactive dashboard for visualizing and analyzing your LinkedIn data export.

## Features

### 8 Interactive Tabs:

1. **Profile Overview** - Personal information, skills distribution, and professional summary
2. **Network Analytics** - Connection growth timeline, top companies in network, endorsements
3. **Career Journey** - Career timeline visualization, education history, certifications
4. **Communications** - Message volume analysis, top conversation partners
5. **Job Search** - Application trends, target companies, saved jobs statistics
6. **Learning** - Course activity, content type distribution, recent learning
7. **Financial** - LinkedIn Premium spending analysis and transaction history
8. **Connections** - Interactive table of all LinkedIn connections with selection and export capabilities

## Installation

```bash
# Install required packages
pip install -r requirements.txt
```

## Usage

```bash
# Run the dashboard
python app.py
```

Then open your browser and navigate to: `http://localhost:8050`

## Data Structure

The dashboard expects LinkedIn data export CSV files in the following structure:

```
/workspace/linkedin/
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

## Key Insights Provided

- **Professional Growth**: Track career progression and role changes over time
- **Network Analysis**: Understand your professional network composition and growth
- **Skill Development**: Visualize skill endorsements and learning patterns
- **Job Search Patterns**: Analyze application trends and target companies
- **Communication Patterns**: Understand messaging frequency and key contacts
- **Investment in Learning**: Track LinkedIn Learning course engagement
- **Financial Overview**: Monitor LinkedIn Premium subscription costs
- **Connection Management**: View, filter, sort, and create shortlists of all LinkedIn connections with persistent JSON export

## Customization

The dashboard can be customized by modifying:
- `app.py` - Main application and tab layouts
- `data_loader.py` - Data processing and cleaning logic
- `assets/style.css` - Visual styling and themes

## Requirements

- Python 3.8+
- Dash 2.14+
- Plotly 5.19+
- Pandas 2.1+