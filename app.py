import dash
from dash import dcc, html, Input, Output, State, ALL, ctx, dash_table
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import pandas as pd
import json
import os
from data_loader import LinkedInDataLoader
from shortlist_viewer import create_shortlist_viewer_tab, register_shortlist_callbacks, get_message_history_display

# Initialize the Dash app with Bootstrap theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, dbc.icons.FONT_AWESOME], suppress_callback_exceptions=True)
app.title = "LinkedIn Data Dashboard"

# Load data
print("Loading LinkedIn data...")
data_loader = LinkedInDataLoader('.')
data = data_loader.load_all_data()

# Define the layout
app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H1("LinkedIn Professional Dashboard", className="text-center mb-4"),
            html.Hr()
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Tabs(
                id="main-tabs",
                active_tab="profile-tab",
                children=[
                    dbc.Tab(label="Profile Overview", tab_id="profile-tab"),
                    dbc.Tab(label="Network Analytics", tab_id="network-tab"),
                    dbc.Tab(label="Career Journey", tab_id="career-tab"),
                    dbc.Tab(label="Connections", tab_id="connections-tab"),
                    dbc.Tab(label="Communications", tab_id="comm-tab"),
                    dbc.Tab(label="Job Search", tab_id="job-tab"),
                    dbc.Tab(label="Learning", tab_id="learning-tab"),
                    dbc.Tab(label="Financial", tab_id="financial-tab"),
                    dbc.Tab(label="Shortlist CRM", tab_id="shortlist-crm-tab"),
                ]
            ),
            html.Div(id="tab-content", className="mt-4")
        ])
    ])
], fluid=True)

# Profile Overview Tab
def create_profile_tab():
    profile = data.get('profile')
    skills = data.get('skills')
    positions = data.get('positions')
    education = data.get('education')

    # Handle empty dataframes
    if profile is None or profile.empty:
        profile = pd.DataFrame({'First Name': [''], 'Last Name': [''], 'Industry': [''], 'Geo Location': [''], 'Summary': ['']})

    # Skills word cloud (using bar chart as alternative)
    skills_fig = None
    if skills is not None and not skills.empty:
        skills_counts = skills['Name'].value_counts().head(20)
        skills_fig = px.bar(
            x=skills_counts.values,
            y=skills_counts.index,
            orientation='h',
            labels={'x': 'Count', 'y': 'Skill'},
            title="Top Skills"
        )
        skills_fig.update_layout(height=400)

    # Current position info
    current_position = "Not specified"
    current_company = "Not specified"
    if positions is not None and not positions.empty:
        current = positions[positions['Finished On'].isna() | (positions['Finished On'] == '')]
        if not current.empty:
            current_position = current.iloc[0]['Title']
            current_company = current.iloc[0]['Company Name']

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Professional Profile"),
                        html.Hr(),
                        html.P(f"Name: {profile['First Name'].iloc[0] if profile is not None else 'N/A'} {profile['Last Name'].iloc[0] if profile is not None else 'N/A'}"),
                        html.P(f"Current Role: {current_position}"),
                        html.P(f"Company: {current_company}"),
                        html.P(f"Industry: {profile['Industry'].iloc[0] if profile is not None and 'Industry' in profile.columns else 'N/A'}"),
                        html.P(f"Location: {profile['Geo Location'].iloc[0] if profile is not None and 'Geo Location' in profile.columns else 'N/A'}"),
                    ])
                ])
            ], width=4),

            dbc.Col([
                dcc.Graph(figure=skills_fig) if skills_fig else html.P("No skills data available")
            ], width=8)
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Professional Summary"),
                        html.P(profile['Summary'].iloc[0] if profile is not None and 'Summary' in profile.columns else "No summary available")
                    ])
                ])
            ])
        ])
    ])

# Network Analytics Tab
def create_network_tab():
    connections = data.get('connections')
    endorsements_received = data.get('endorsement_received')
    recommendations_received = data.get('recommendations_received')

    # Connection timeline
    connection_fig = None
    if connections is not None and not connections.empty and 'Connected On' in connections.columns:
        connections_copy = connections.copy()
        # Parse the date format "16 Sep 2025"
        connections_copy['Connected On'] = pd.to_datetime(connections_copy['Connected On'], format='%d %b %Y', errors='coerce')
        connections_copy = connections_copy.dropna(subset=['Connected On'])

        if not connections_copy.empty:
            connections_copy = connections_copy.sort_values('Connected On')
            connections_copy['Cumulative'] = range(1, len(connections_copy) + 1)

            connection_fig = px.line(
                connections_copy,
                x='Connected On',
                y='Cumulative',
                title='Network Growth Over Time',
                labels={'Cumulative': 'Total Connections', 'Connected On': 'Date'}
            )
            connection_fig.update_layout(height=380)

    # Top companies in network
    company_fig = None
    if connections is not None and not connections.empty and 'Company' in connections.columns:
        top_companies = connections['Company'].value_counts().head(15)
        company_fig = px.bar(
            x=top_companies.index,
            y=top_companies.values,
            labels={'x': 'Company', 'y': 'Number of Connections'},
            title='Top Companies in Your Network'
        )

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Network Statistics"),
                        html.Hr(),
                        html.P(f"Total Connections: {len(connections) if connections is not None else 0}", style={'fontSize': '1.2rem'}),
                        html.P(f"Endorsements Received: {len(endorsements_received) if endorsements_received is not None else 0}", style={'fontSize': '1.2rem'}),
                        html.P(f"Recommendations Received: {len(recommendations_received) if recommendations_received is not None else 0}", style={'fontSize': '1.2rem'}),
                    ])
                ], style={'height': '400px'})
            ], width=4),

            dbc.Col([
                dcc.Graph(figure=connection_fig, style={'height': '400px'}) if connection_fig else html.P("No connection timeline data available")
            ], width=8)
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=company_fig) if company_fig else html.P("No company data available")
            ])
        ])
    ])

# Career Journey Tab
def create_career_tab():
    positions = data.get('positions')
    education = data.get('education')
    certifications = data.get('certifications')

    # Career timeline
    timeline_fig = None
    if positions is not None and not positions.empty:
        positions_copy = positions.copy()
        # Parse dates without timezone info to avoid conflicts
        positions_copy['Started On'] = pd.to_datetime(positions_copy['Started On'], errors='coerce').dt.tz_localize(None)
        positions_copy['Finished On'] = pd.to_datetime(positions_copy['Finished On'], errors='coerce').dt.tz_localize(None)
        positions_copy = positions_copy.dropna(subset=['Started On'])

        # Create timeline visualization
        timeline_data = []
        for _, row in positions_copy.iterrows():
            # Ensure dates are timezone-naive
            start_date = row['Started On']
            end_date = row['Finished On'] if pd.notna(row['Finished On']) else pd.Timestamp.now().tz_localize(None)

            timeline_data.append({
                'Task': f"{row['Company Name']}",
                'Start': start_date,
                'Finish': end_date,
                'Title': row['Title'],
                'Company': row['Company Name']
            })

        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)

            # Create a Gantt chart instead of timeline for better compatibility
            timeline_fig = go.Figure()

            # Sort by start date for better visualization
            df_timeline = df_timeline.sort_values('Start').reset_index(drop=True)

            for idx, (_, row) in enumerate(df_timeline.iterrows()):
                # Format dates for display
                start_str = row['Start'].strftime('%b %Y')
                end_str = row['Finish'].strftime('%b %Y') if pd.notna(row['Finish']) else 'Present'

                timeline_fig.add_trace(go.Scatter(
                    x=[row['Start'], row['Finish'], row['Finish'], row['Start'], row['Start']],
                    y=[idx-0.4, idx-0.4, idx+0.4, idx+0.4, idx-0.4],
                    fill='toself',
                    fillcolor='rgba(0, 102, 204, 0.6)',
                    line=dict(color='rgba(0, 102, 204, 1)', width=1),
                    hovertemplate=f"<b>{row['Company']}</b><br>{row['Title']}<br>{start_str} - {end_str}<extra></extra>",
                    showlegend=False,
                    mode='lines'
                ))

            timeline_fig.update_layout(
                title="Career Timeline",
                xaxis=dict(title="", type='date', tickformat='%Y'),
                yaxis=dict(
                    title="",
                    tickmode='array',
                    tickvals=list(range(len(df_timeline))),
                    ticktext=[f"{row['Title']} @ {row['Company']}" for _, row in df_timeline.iterrows()],
                    automargin=True
                ),
                height=max(400, len(df_timeline) * 80),
                hovermode='closest',
                margin=dict(l=350)  # More space for role titles
            )

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=timeline_fig) if timeline_fig else html.P("No career timeline data available")
            ])
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Education"),
                        html.Hr(),
                        html.Div([
                            html.Div([
                                html.P([
                                    html.Strong(f"{row['School Name']}"),
                                    html.Br(),
                                    f"{row['Degree Name'] if pd.notna(row['Degree Name']) and row['Degree Name'] else ''}",
                                    html.Br() if pd.notna(row['Degree Name']) and row['Degree Name'] else None,
                                    html.Small(
                                        f"{str(row['Start Date']).split('-')[0] if pd.notna(row['Start Date']) and str(row['Start Date']) != 'nan' else ''}"
                                        f"{' - ' if pd.notna(row['Start Date']) and pd.notna(row['End Date']) else ''}"
                                        f"{str(row['End Date']).split('-')[0] if pd.notna(row['End Date']) and str(row['End Date']) != 'nan' else ''}",
                                        className="text-muted"
                                    ) if (pd.notna(row['Start Date']) or pd.notna(row['End Date'])) else None
                                ], className="mb-3")
                            ]) for _, row in education.iterrows()
                        ] if education is not None and not education.empty else [html.P("No education data available")])
                    ])
                ])
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Certifications"),
                        html.Hr(),
                        html.Div([
                            html.P(row['Name']) for _, row in certifications.iterrows()
                        ] if certifications is not None and not certifications.empty else [html.P("No certification data available")])
                    ])
                ])
            ], width=6)
        ])
    ])

# Communications Tab
def create_comm_tab():
    messages = data.get('messages')
    profile = data.get('profile')

    # Get the user's name from profile
    user_name = None
    if profile is not None and not profile.empty:
        user_name = f"{profile.iloc[0].get('First Name', '')} {profile.iloc[0].get('Last Name', '')}".strip()

    # Message volume over time
    message_fig = None
    if messages is not None and not messages.empty and 'DATE' in messages.columns:
        messages_copy = messages.copy()
        messages_copy['DATE'] = pd.to_datetime(messages_copy['DATE'], errors='coerce')
        messages_copy = messages_copy.dropna(subset=['DATE'])

        if not messages_copy.empty:
            messages_copy['Month'] = messages_copy['DATE'].dt.to_period('M')
            message_counts = messages_copy.groupby('Month').size().reset_index(name='Count')
            message_counts['Month'] = message_counts['Month'].astype(str)

            message_fig = px.line(
                message_counts,
                x='Month',
                y='Count',
                title='Message Volume Over Time',
                labels={'Count': 'Number of Messages', 'Month': 'Month'}
            )

    # Top conversation partners with clickable names - group by counterparty
    top_partners_list = None
    if messages is not None and not messages.empty and 'FROM' in messages.columns and 'TO' in messages.columns:
        # Create a counterparty column - the person who is NOT the user
        messages_copy = messages.copy()

        # Determine counterparty for each message
        def get_counterparty(row):
            if user_name and row['FROM'] == user_name:
                return row.get('TO', 'Unknown')
            else:
                return row['FROM']

        messages_copy['Counterparty'] = messages_copy.apply(get_counterparty, axis=1)

        # Get top 25 conversation partners by counterparty
        top_partners = messages_copy['Counterparty'].value_counts().head(25)

        # Create clickable list
        top_partners_list = html.Div([
            dbc.ListGroup([
                dbc.ListGroupItem(
                    [
                        html.Div([
                            html.Span(name, className="fw-bold"),
                            dbc.Badge(f"{count} messages", color="primary", className="float-end")
                        ])
                    ],
                    id={"type": "partner-item", "name": name},
                    action=True,
                    className="d-flex justify-content-between align-items-center"
                )
                for name, count in top_partners.items()
            ])
        ])

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=message_fig) if message_fig else html.P("No message timeline data available")
            ])
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Top Conversation Partners (Click to view history)"),
                        html.Hr(),
                        top_partners_list if top_partners_list else html.P("No conversation partner data available")
                    ])
                ], style={"height": "600px", "overflowY": "auto"})
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Message History", id="history-title"),
                        html.Hr(),
                        html.Div(id="message-history", children=[
                            html.P("Select a contact to view message history", className="text-muted")
                        ])
                    ])
                ], style={"height": "600px", "overflowY": "auto"})
            ], width=6)
        ]),

        # Store component to hold selected partner
        dcc.Store(id="selected-partner", data=None)
    ])

# Job Search Tab
def create_job_tab():
    job_applications = data.get('job_applications')
    saved_jobs = data.get('saved_jobs')
    job_alerts = data.get('saved_job_alerts')

    # Application timeline
    application_fig = None
    if job_applications is not None and not job_applications.empty and 'Application Date' in job_applications.columns:
        job_apps_copy = job_applications.copy()
        job_apps_copy['Application Date'] = pd.to_datetime(job_apps_copy['Application Date'], errors='coerce')
        job_apps_copy = job_apps_copy.dropna(subset=['Application Date'])

        if not job_apps_copy.empty:
            job_apps_copy['Month'] = job_apps_copy['Application Date'].dt.to_period('M')
            app_counts = job_apps_copy.groupby('Month').size().reset_index(name='Count')
            app_counts['Month'] = app_counts['Month'].astype(str)

            application_fig = px.bar(
                app_counts,
                x='Month',
                y='Count',
                title='Job Applications Over Time',
                labels={'Count': 'Number of Applications', 'Month': 'Month'}
            )
            application_fig.update_layout(height=380)

    # Top target companies
    target_companies_fig = None
    if job_applications is not None and not job_applications.empty and 'Company Name' in job_applications.columns:
        top_companies = job_applications['Company Name'].value_counts().head(10)
        target_companies_fig = px.bar(
            x=top_companies.index,
            y=top_companies.values,
            labels={'x': 'Company', 'y': 'Number of Applications'},
            title='Most Applied Companies'
        )

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("Job Search Statistics"),
                        html.Hr(),
                        html.P(f"Total Applications: {len(job_applications) if job_applications is not None else 0}", style={'fontSize': '1.2rem'}),
                        html.P(f"Saved Jobs: {len(saved_jobs) if saved_jobs is not None else 0}", style={'fontSize': '1.2rem'}),
                        html.P(f"Job Alerts: {len(job_alerts) if job_alerts is not None else 0}", style={'fontSize': '1.2rem'}),
                    ])
                ], style={'height': '400px'})
            ], width=4),

            dbc.Col([
                dcc.Graph(figure=application_fig, style={'height': '400px'}) if application_fig else html.P("No application timeline data available")
            ], width=8)
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=target_companies_fig) if target_companies_fig else html.P("No target company data available")
            ])
        ])
    ])

# Learning Tab
def create_learning_tab():
    learning = data.get('learning')

    # Learning content type distribution
    content_type_fig = None
    if learning is not None and not learning.empty and 'Content Type' in learning.columns:
        content_types = learning['Content Type'].value_counts()
        content_type_fig = px.pie(
            values=content_types.values,
            names=content_types.index,
            title='Learning Content Type Distribution'
        )

    # Recent courses
    recent_courses = None
    if learning is not None and not learning.empty and 'Content Last Watched Date (if viewed)' in learning.columns:
        learning_copy = learning.copy()
        learning_copy['Content Last Watched Date (if viewed)'] = pd.to_datetime(
            learning_copy['Content Last Watched Date (if viewed)'],
            errors='coerce'
        )
        recent_courses = learning_copy.dropna(subset=['Content Last Watched Date (if viewed)'])
        recent_courses = recent_courses.sort_values('Content Last Watched Date (if viewed)', ascending=False).head(10)

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=content_type_fig) if content_type_fig else html.P("No learning content type data available")
            ], width=6),

            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Recent Learning Activity"),
                        html.Hr(),
                        html.Div([
                            html.P([
                                html.Strong(row['Content Title']),
                                html.Br(),
                                html.Small(f"Last watched: {row['Content Last Watched Date (if viewed)'].strftime('%Y-%m-%d') if pd.notna(row['Content Last Watched Date (if viewed)']) else 'N/A'}")
                            ], className="mb-2") for _, row in recent_courses.iterrows()
                        ] if recent_courses is not None and not recent_courses.empty else [html.P("No recent learning activity")])
                    ])
                ])
            ], width=6)
        ])
    ])

# Financial Tab
def create_financial_tab():
    receipts = data.get('receipts_v2')

    # Spending over time
    spending_fig = None
    if receipts is not None and not receipts.empty and 'Transaction Made At' in receipts.columns:
        receipts_copy = receipts.copy()
        receipts_copy['Transaction Made At'] = pd.to_datetime(receipts_copy['Transaction Made At'], errors='coerce')
        receipts_copy = receipts_copy.dropna(subset=['Transaction Made At'])

        if not receipts_copy.empty and 'Total Amount' in receipts_copy.columns:
            receipts_copy['Year'] = receipts_copy['Transaction Made At'].dt.year
            spending_by_year = receipts_copy.groupby('Year')['Total Amount'].sum().reset_index()

            spending_fig = px.bar(
                spending_by_year,
                x='Year',
                y='Total Amount',
                title='LinkedIn Premium Spending by Year',
                labels={'Total Amount': 'Amount (AUD)', 'Year': 'Year'}
            )

    # Transaction details
    transaction_details = None
    if receipts is not None and not receipts.empty:
        transaction_details = receipts[['Transaction Made At', 'Description', 'Total Amount', 'Currency Code']].copy()
        transaction_details = transaction_details.sort_values('Transaction Made At', ascending=False)

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dcc.Graph(figure=spending_fig) if spending_fig else html.P("No spending data available")
            ])
        ], className="mb-4"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("Transaction History"),
                        html.Hr(),
                        dbc.Table.from_dataframe(
                            transaction_details.head(10),
                            striped=True,
                            bordered=True,
                            hover=True,
                            responsive=True
                        ) if transaction_details is not None and not transaction_details.empty else html.P("No transaction data available")
                    ])
                ])
            ])
        ])
    ])

# Connections Tab
def create_connections_tab():
    connections = data.get('connections')

    if connections is None or connections.empty:
        return html.P("No connections data available")

    # Prepare data for display
    display_df = connections.copy()

    # Add a selection column (will be managed by callback)
    shortlist_path = 'connections_shortlist.json'
    shortlist = []
    shortlist_names = []
    if os.path.exists(shortlist_path):
        try:
            with open(shortlist_path, 'r') as f:
                shortlist_data = json.load(f)
                # Handle both old format (list of names) and new format (list of objects)
                if shortlist_data and isinstance(shortlist_data[0], str):
                    # Old format - just names
                    shortlist_names = shortlist_data
                elif shortlist_data:
                    # New format - objects with details
                    shortlist = shortlist_data
                    shortlist_names = [item['name'] for item in shortlist_data]
        except:
            shortlist = []
            shortlist_names = []

    # Create full name column
    display_df['Full Name'] = display_df['First Name'].fillna('') + ' ' + display_df['Last Name'].fillna('')
    display_df['Full Name'] = display_df['Full Name'].str.strip()

    # Format Connected On date as YYYY-MM-DD
    if 'Connected On' in display_df.columns:
        display_df['Connected On'] = pd.to_datetime(display_df['Connected On'], format='%d %b %Y', errors='coerce').dt.strftime('%Y-%m-%d')

    # Convert URLs to markdown links
    if 'URL' in display_df.columns:
        display_df['URL'] = display_df['URL'].apply(
            lambda x: f'[View Profile]({x})' if pd.notna(x) and x else ''
        )

    # Reorder columns for better display
    columns_order = ['Full Name', 'Company', 'Position', 'Connected On', 'Email Address', 'URL']
    available_columns = [col for col in columns_order if col in display_df.columns]
    display_df = display_df[available_columns]

    # Find which rows should be selected based on shortlist
    selected_rows = []
    for idx, row in display_df.iterrows():
        if row['Full Name'] in shortlist_names:
            selected_rows.append(idx)

    return dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H4("All Connections", className="mb-3"),
                        html.P(f"Total connections: {len(connections)}", className="text-muted"),
                        html.P(f"Shortlisted: {len(shortlist)}", id="shortlist-count", className="text-muted"),
                        dbc.Button(
                            "Clear Shortlist",
                            id="clear-shortlist-btn",
                            color="danger",
                            size="sm",
                            className="mb-3"
                        )
                    ])
                ])
            ], width=12)
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dag.AgGrid(
                    id='connections-table',
                    rowData=display_df.to_dict('records'),
                    columnDefs=[
                        {"field": "Full Name", "headerName": "Name", "resizable": True,
                         "checkboxSelection": True, "headerCheckboxSelection": True,
                         "sortable": True, "filter": True, "floatingFilter": True, "width": 200},
                        {"field": "Company", "headerName": "Company", "resizable": True,
                         "sortable": True, "filter": True, "floatingFilter": True, "width": 200},
                        {"field": "Position", "headerName": "Position", "resizable": True,
                         "sortable": True, "filter": True, "floatingFilter": True, "width": 200},
                        {"field": "Connected On", "headerName": "Connected", "resizable": True,
                         "sortable": True, "filter": True, "floatingFilter": True, "width": 120},
                        {"field": "Email Address", "headerName": "Email", "resizable": True,
                         "sortable": True, "filter": True, "floatingFilter": True, "width": 180},
                        {"field": "URL", "headerName": "Profile", "resizable": True,
                         "cellRenderer": "markdown", "width": 120}
                    ],

                    # Grid options
                    defaultColDef={
                        "resizable": True,
                        "sortable": True,
                        "filter": True,
                        "minWidth": 100
                    },

                    # Selection configuration
                    dashGridOptions={
                        "rowSelection": "multiple",
                        "suppressRowClickSelection": True,
                        "rowMultiSelectWithClick": False,
                        "animateRows": True,
                        "pagination": False,  # Continuous scrolling
                        "domLayout": "normal",
                        "enableCellTextSelection": True,
                        "ensureDomOrder": True
                    },

                    # Pre-select rows based on shortlist - return actual row data, not indices
                    selectedRows=[display_df.iloc[idx].to_dict() for idx in selected_rows],

                    # Styling
                    style={"height": "calc(100vh - 350px)", "width": "100%"},
                    className="ag-theme-alpine"
                )
            ], width=12)
        ]),

        # Hidden store for shortlist
        dcc.Store(id='shortlist-store', data=shortlist)
    ])

# Callback to handle partner selection and display message history
@app.callback(
    [Output("message-history", "children"),
     Output("history-title", "children")],
    [Input({"type": "partner-item", "name": ALL}, "n_clicks")],
    prevent_initial_call=True
)
def display_message_history_comm(n_clicks):
    # Check if any button was triggered
    if not ctx.triggered:
        return [html.P("Select a contact to view message history", className="text-muted")], "Message History"

    # Get the triggered button's ID
    triggered = ctx.triggered[0]
    if not triggered or 'prop_id' not in triggered:
        return [html.P("Select a contact to view message history", className="text-muted")], "Message History"

    # Parse the triggered ID to get the partner name
    try:
        button_id = json.loads(triggered['prop_id'].split('.')[0])
        selected_partner = button_id.get('name')
    except:
        return [html.P("Error selecting contact", className="text-muted")], "Message History"

    if not selected_partner:
        return [html.P("Select a contact to view message history", className="text-muted")], "Message History"

    # Use shared helper function
    messages_df = data.get('messages')
    profile_df = data.get('profile')
    message_display = get_message_history_display(selected_partner, messages_df, profile_df)

    return message_display, f"Messages with {selected_partner}"

# Callback to render tab content
@app.callback(
    Output("tab-content", "children"),
    Input("main-tabs", "active_tab")
)
def render_tab_content(active_tab):
    if active_tab == "profile-tab":
        return create_profile_tab()
    elif active_tab == "network-tab":
        return create_network_tab()
    elif active_tab == "career-tab":
        return create_career_tab()
    elif active_tab == "connections-tab":
        return create_connections_tab()
    elif active_tab == "comm-tab":
        return create_comm_tab()
    elif active_tab == "job-tab":
        return create_job_tab()
    elif active_tab == "learning-tab":
        return create_learning_tab()
    elif active_tab == "financial-tab":
        return create_financial_tab()
    elif active_tab == "shortlist-crm-tab":
        return create_shortlist_viewer_tab()
    return html.P("Select a tab to view content")

# Callback to handle connections selection and persist to JSON
@app.callback(
    [Output("shortlist-store", "data"),
     Output("shortlist-count", "children"),
     Output("connections-table", "selectedRows")],
    [Input("connections-table", "selectedRows"),
     Input("clear-shortlist-btn", "n_clicks")],
    [State("connections-table", "rowData")],
    prevent_initial_call=True
)
def update_shortlist(selected_rows, clear_clicks, table_data):
    shortlist_path = 'connections_shortlist.json'

    # Handle clear button
    if ctx.triggered and ctx.triggered[0]['prop_id'] == 'clear-shortlist-btn.n_clicks':
        # Clear the shortlist and deselect all rows
        with open(shortlist_path, 'w') as f:
            json.dump([], f)
        # Return empty list to clear visual selection
        return [], "Shortlisted: 0", []

    # Handle row selections - AG Grid returns the actual row data, not indices
    # selected_rows can be None (no selection) or empty list (deselected all)
    if selected_rows is None:
        selected_rows = []

    # Extract complete connection info from selected rows
    shortlist = []
    for row in selected_rows:
        connection = {
            'name': row.get('Full Name', ''),
            'company': row.get('Company', ''),
            'position': row.get('Position', ''),
            'profile_url': row.get('URL', '').replace('[View Profile](', '').replace(')', '') if row.get('URL') else '',
            'connected_on': row.get('Connected On', ''),
            'email': row.get('Email Address', '')
        }
        shortlist.append(connection)

    # Save to JSON file immediately with all details
    with open(shortlist_path, 'w') as f:
        json.dump(shortlist, f, indent=2)

    # Return the actual row data objects for AG Grid selectedRows (not indices!)
    # AG Grid expects objects, not indices
    return shortlist, f"Shortlisted: {len(shortlist)}", selected_rows

# Register shortlist CRM callbacks
register_shortlist_callbacks(app, data)

if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=8050)
