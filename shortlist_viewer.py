"""
CRM-style Shortlist Viewer Tab for LinkedIn Dashboard

This module provides a tab for viewing and managing the connections shortlist
with CRM-like features including status tracking and comments.
"""

from dash import dcc, html, Input, Output, State, ctx
import dash_bootstrap_components as dbc
import dash_ag_grid as dag
import pandas as pd
import json
import os
from datetime import datetime

# Constants
SHORTLIST_PATH = 'connections_shortlist.json'
CRM_ARCHIVE_PATH = 'crm_archive.json'

STATUS_OPTIONS = [
    {"label": "New", "value": "new"},
    {"label": "To Contact", "value": "to_contact"},
    {"label": "Contacted", "value": "contacted"},
    {"label": "In Conversation", "value": "in_conversation"},
    {"label": "Meeting Scheduled", "value": "meeting_scheduled"},
    {"label": "On Hold", "value": "on_hold"},
    {"label": "Closed (Positive)", "value": "closed_positive"},
    {"label": "Closed (Negative)", "value": "closed_negative"},
]

STATUS_COLORS = {
    "new": "secondary",
    "to_contact": "info",
    "contacted": "primary",
    "in_conversation": "warning",
    "meeting_scheduled": "success",
    "on_hold": "light",
    "closed_positive": "success",
    "closed_negative": "danger",
}

STATUS_LABELS = {opt["value"]: opt["label"] for opt in STATUS_OPTIONS}


def has_data(df):
    """Check if a DataFrame has data (not None and not empty)."""
    return df is not None and not df.empty


def shortlist_to_row_data(shortlist):
    """Convert shortlist entries to AG Grid row data format."""
    return [
        {
            "name": entry.get("name", ""),
            "company": entry.get("company", ""),
            "position": entry.get("position", ""),
            "status": entry.get("status", "new"),
            "status_label": STATUS_LABELS.get(entry.get("status", "new"), "New"),
            "connected_on": entry.get("connected_on", ""),
            "profile_url": entry.get("profile_url", ""),
            "email": entry.get("email", ""),
            "comments": entry.get("comments", ""),
        }
        for entry in shortlist
    ]


def create_stats_items(shortlist):
    """Create statistics items showing counts per status."""
    counts = get_status_counts(shortlist)
    total = len(shortlist)

    items = [
        html.Div([
            html.Span("Total: ", className="fw-bold"),
            dbc.Badge(str(total), color="dark", className="ms-1")
        ], className="mb-2")
    ]

    for opt in STATUS_OPTIONS:
        status_value = opt["value"]
        count = counts[status_value]
        if count > 0:
            items.append(
                html.Div([
                    html.Span(f"{opt['label']}: "),
                    dbc.Badge(str(count), color=STATUS_COLORS[status_value], className="ms-1")
                ], className="mb-1")
            )

    return items


def get_message_history_display(contact_name, messages_df, profile_df):
    """
    Get message history display components for a contact.

    Args:
        contact_name: Name of the contact to get messages for
        messages_df: DataFrame containing messages (from data['messages'])
        profile_df: DataFrame containing user profile (from data['profile'])

    Returns:
        List of Dash components displaying the message history
    """
    if not has_data(messages_df):
        return [html.P("No messages available", className="text-muted")]

    # Get user name from profile
    user_name = None
    if has_data(profile_df):
        user_name = f"{profile_df.iloc[0].get('First Name', '')} {profile_df.iloc[0].get('Last Name', '')}".strip()

    # Filter messages for this contact (either FROM or TO)
    if 'TO' in messages_df.columns:
        partner_messages = messages_df[
            (messages_df['FROM'] == contact_name) |
            (messages_df['TO'] == contact_name)
        ].copy()
    else:
        partner_messages = messages_df[
            messages_df['FROM'] == contact_name
        ].copy()

    if partner_messages.empty:
        return [html.P(f"No messages found with {contact_name}", className="text-muted")]

    # Sort by date
    partner_messages['DATE'] = pd.to_datetime(partner_messages['DATE'], errors='coerce')
    partner_messages = partner_messages.sort_values('DATE', ascending=False)

    # Create message display
    message_display = []
    for _, msg in partner_messages.head(50).iterrows():
        # Format date
        date_str = msg['DATE'].strftime('%Y-%m-%d %H:%M') if pd.notna(msg['DATE']) else 'Unknown date'

        # Determine direction
        from_person = msg.get('FROM', 'Unknown')
        to_person = msg.get('TO', 'Unknown') if 'TO' in msg else 'Unknown'

        if user_name and from_person == user_name:
            direction = f"You -> {to_person}"
        else:
            direction = f"{from_person} -> You"

        # Get message content
        content = msg.get('CONTENT', '')
        if pd.isna(content) or content == '':
            content = "(No content available)"

        # Create message card
        message_card = dbc.Card([
            dbc.CardBody([
                html.Div([
                    html.Small(f"{date_str} | {direction}", className="text-muted"),
                    html.Hr(className="my-1"),
                    html.P(content, className="mb-0", style={"whiteSpace": "pre-wrap", "fontSize": "0.9rem"})
                ])
            ], style={"padding": "0.5rem"})
        ], className="mb-2")

        message_display.append(message_card)

    # Add note if truncated
    if len(partner_messages) > 50:
        message_display.append(
            html.P(f"Showing 50 most recent of {len(partner_messages)} messages",
                   className="text-muted text-center mt-2")
        )

    return message_display


def load_shortlist_with_defaults():
    """Load shortlist JSON with default values for CRM fields."""
    shortlist = []
    if os.path.exists(SHORTLIST_PATH):
        try:
            with open(SHORTLIST_PATH, 'r') as f:
                shortlist = json.load(f)
        except (json.JSONDecodeError, IOError):
            shortlist = []

    # Add defaults for missing CRM fields
    for entry in shortlist:
        if 'status' not in entry:
            entry['status'] = 'new'
        if 'comments' not in entry:
            entry['comments'] = ''
        if 'last_updated' not in entry:
            entry['last_updated'] = None

    return shortlist


def save_shortlist(shortlist):
    """Save shortlist to JSON file."""
    with open(SHORTLIST_PATH, 'w') as f:
        json.dump(shortlist, f, indent=2)


def load_crm_archive():
    """Load CRM archive from JSON file. Returns dict keyed by contact name."""
    if os.path.exists(CRM_ARCHIVE_PATH):
        try:
            with open(CRM_ARCHIVE_PATH, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_to_crm_archive(name, status, comments, last_updated):
    """Save CRM data for a contact to the archive."""
    archive = load_crm_archive()
    archive[name] = {
        'status': status,
        'comments': comments,
        'last_updated': last_updated
    }
    with open(CRM_ARCHIVE_PATH, 'w') as f:
        json.dump(archive, f, indent=2)


def get_crm_data_for_contact(name):
    """Get CRM data for a contact from the archive. Returns defaults if not found."""
    archive = load_crm_archive()
    if name in archive:
        data = archive[name]
        return {
            'status': data.get('status', 'new'),
            'comments': data.get('comments', ''),
            'last_updated': data.get('last_updated')
        }
    return {'status': 'new', 'comments': '', 'last_updated': None}


def get_status_counts(shortlist):
    """Calculate counts per status."""
    counts = {opt["value"]: 0 for opt in STATUS_OPTIONS}
    for entry in shortlist:
        status = entry.get('status', 'new')
        if status in counts:
            counts[status] += 1
    return counts


def create_stats_card(shortlist):
    """Create statistics card showing counts per status."""
    return dbc.Card([
        dbc.CardHeader(html.H5("Statistics", className="mb-0")),
        dbc.CardBody(create_stats_items(shortlist), id="shortlist-stats")
    ])


def create_shortlist_viewer_tab():
    """Create the Shortlist CRM tab layout."""
    shortlist = load_shortlist_with_defaults()
    row_data = shortlist_to_row_data(shortlist)

    return dbc.Container([
        dbc.Row([
            # Left column: Stats + Contact List
            dbc.Col([
                create_stats_card(shortlist),
                html.Div(className="mb-3"),
                dbc.Card([
                    dbc.CardHeader([
                        html.H5("Contacts", className="mb-0 d-inline"),
                        dbc.Select(
                            id="shortlist-status-filter",
                            options=[{"label": "All Statuses", "value": "all"}] + STATUS_OPTIONS,
                            value="all",
                            size="sm",
                            className="d-inline-block ms-3",
                            style={"width": "150px"}
                        )
                    ]),
                    dbc.CardBody([
                        dag.AgGrid(
                            id='shortlist-crm-table',
                            rowData=row_data,
                            columnDefs=[
                                {
                                    "field": "name",
                                    "headerName": "Name",
                                    "flex": 2,
                                    "sortable": True,
                                    "filter": True,
                                    "floatingFilter": True,
                                },
                                {
                                    "field": "company",
                                    "headerName": "Company",
                                    "flex": 2,
                                    "sortable": True,
                                    "filter": True,
                                    "floatingFilter": True,
                                },
                                {
                                    "field": "status_label",
                                    "headerName": "Status",
                                    "flex": 1,
                                    "sortable": True,
                                    "filter": True,
                                },
                            ],
                            defaultColDef={"resizable": True, "minWidth": 80},
                            dashGridOptions={
                                "rowSelection": "single",
                                "animateRows": True,
                            },
                            getRowId="params.data.name",
                            style={"height": "400px", "width": "100%"},
                            className="ag-theme-alpine"
                        )
                    ], style={"padding": "0.5rem"})
                ])
            ], width=5),

            # Right column: Detail panel + Message history
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader(html.H5("Contact Details", id="shortlist-contact-name", className="mb-0")),
                    dbc.CardBody([
                        # Contact info display
                        html.Div(id="shortlist-contact-info", children=[
                            html.P("Select a contact from the list to view details", className="text-muted")
                        ]),
                        html.Hr(),

                        # Editable section
                        dbc.Form([
                            dbc.Label("Status", className="fw-bold"),
                            dbc.Select(
                                id="shortlist-status-dropdown",
                                options=STATUS_OPTIONS,
                                value="new",
                                disabled=True,
                                className="mb-3"
                            ),

                            dbc.Label("Comments", className="fw-bold"),
                            dbc.Textarea(
                                id="shortlist-comments-textarea",
                                placeholder="Add notes about this contact...",
                                style={"height": "100px"},
                                disabled=True,
                                className="mb-3"
                            ),

                            dbc.Button(
                                "Save Changes",
                                id="shortlist-save-btn",
                                color="primary",
                                disabled=True,
                            ),
                        ]),
                    ])
                ], className="mb-3"),

                # Message history card
                dbc.Card([
                    dbc.CardHeader(html.H5("Message History", className="mb-0")),
                    dbc.CardBody([
                        html.Div(
                            id="shortlist-message-history",
                            children=[html.P("Select a contact to view message history", className="text-muted")],
                            style={"maxHeight": "300px", "overflowY": "auto"}
                        )
                    ])
                ])
            ], width=7),
        ]),

        # Hidden stores
        dcc.Store(id='selected-shortlist-contact', data=None),
        dcc.Store(id='shortlist-store-full', data=row_data),
        dcc.Store(id='shortlist-selected-index', data=None),
        dcc.Store(id='keyboard-event', data={'key': None, 'timestamp': 0}),
        dcc.Interval(id='keyboard-poll', interval=100, n_intervals=0, disabled=False),

        # Toast for save feedback
        dbc.Toast(
            id="shortlist-save-toast",
            header="Saved",
            is_open=False,
            dismissable=True,
            duration=3000,
            icon="success",
            style={"position": "fixed", "top": 66, "right": 10, "width": 350, "zIndex": 1050},
        ),
    ], fluid=True)


def register_shortlist_callbacks(app, data):
    """Register all callbacks for the shortlist viewer tab.

    Args:
        app: Dash application instance
        data: Data dictionary containing 'messages' and 'profile' DataFrames
    """

    # Status values mapped to number keys 1-8
    STATUS_KEY_MAP = {
        '1': 'new',
        '2': 'to_contact',
        '3': 'contacted',
        '4': 'in_conversation',
        '5': 'meeting_scheduled',
        '6': 'on_hold',
        '7': 'closed_positive',
        '8': 'closed_negative',
    }

    # Clientside callback to capture global keyboard events
    app.clientside_callback(
        """
        function(n) {
            // Set up listener on first call
            if (!window._shortlistKbListenerSetup) {
                window._shortlistKbListenerSetup = true;
                window._shortlistPendingKey = null;
                window._shortlistKeyTimestamp = 0;

                document.addEventListener('keydown', function(e) {
                    // Check if we're in an input field
                    const activeTag = document.activeElement.tagName.toLowerCase();
                    if (activeTag === 'input' || activeTag === 'textarea' || activeTag === 'select') {
                        return;
                    }

                    // Check if CRM tab is active by looking for the grid
                    const crmTable = document.getElementById('shortlist-crm-table');
                    if (!crmTable) {
                        return;
                    }
                    // Check if the table is visible (tab is active)
                    if (crmTable.offsetParent === null) {
                        return;
                    }

                    // Handle arrow keys and number keys 1-8
                    const key = e.key;
                    if (key === 'ArrowUp' || key === 'ArrowDown' || (key >= '1' && key <= '8')) {
                        e.preventDefault();
                        window._shortlistPendingKey = key;
                        window._shortlistKeyTimestamp = Date.now();
                    }
                });
            }

            // Return pending key if any
            if (window._shortlistPendingKey) {
                const result = {key: window._shortlistPendingKey, timestamp: window._shortlistKeyTimestamp};
                window._shortlistPendingKey = null;
                return result;
            }
            return window.dash_clientside.no_update;
        }
        """,
        Output('keyboard-event', 'data'),
        Input('keyboard-poll', 'n_intervals'),
    )

    @app.callback(
        [Output("shortlist-contact-info", "children"),
         Output("shortlist-contact-name", "children"),
         Output("shortlist-status-dropdown", "value"),
         Output("shortlist-status-dropdown", "disabled"),
         Output("shortlist-comments-textarea", "value"),
         Output("shortlist-comments-textarea", "disabled"),
         Output("shortlist-save-btn", "disabled"),
         Output("selected-shortlist-contact", "data")],
        [Input("shortlist-crm-table", "selectedRows")],
        prevent_initial_call=True
    )
    def display_contact_details(selected_rows):
        """Display details when a contact is selected."""
        if not selected_rows or len(selected_rows) == 0:
            return (
                [html.P("Select a contact from the list to view details", className="text-muted")],
                "Contact Details",
                "new",
                True,
                "",
                True,
                True,
                None
            )

        contact = selected_rows[0]
        name = contact.get("name", "Unknown")
        company = contact.get("company", "N/A") or "N/A"
        position = contact.get("position", "N/A") or "N/A"
        connected_on = contact.get("connected_on", "N/A") or "N/A"
        profile_url = contact.get("profile_url", "")
        email = contact.get("email", "") or ""
        status = contact.get("status", "new")
        comments = contact.get("comments", "")

        # Build contact info display
        info_items = [
            html.P([html.Strong("Company: "), company]),
            html.P([html.Strong("Position: "), position]),
            html.P([html.Strong("Connected: "), connected_on]),
        ]

        if email:
            info_items.append(html.P([html.Strong("Email: "), email]))

        if profile_url:
            info_items.append(
                html.P([
                    html.Strong("Profile: "),
                    html.A("View on LinkedIn", href=profile_url, target="_blank")
                ])
            )

        return (
            info_items,
            name,
            status,
            False,
            comments or "",
            False,
            False,
            {"name": name}
        )

    @app.callback(
        [Output("shortlist-save-toast", "is_open"),
         Output("shortlist-save-toast", "children"),
         Output("shortlist-crm-table", "rowData"),
         Output("shortlist-stats", "children"),
         Output("shortlist-store-full", "data")],
        [Input("shortlist-save-btn", "n_clicks")],
        [State("selected-shortlist-contact", "data"),
         State("shortlist-status-dropdown", "value"),
         State("shortlist-comments-textarea", "value")],
        prevent_initial_call=True
    )
    def save_contact_changes(n_clicks, selected_contact, status, comments):
        """Save changes to the selected contact."""
        from dash import no_update

        if not n_clicks or not selected_contact:
            return no_update, no_update, no_update, no_update, no_update

        contact_name = selected_contact.get("name")
        if not contact_name:
            return True, "Error: No contact selected", no_update, no_update, no_update

        # Load current shortlist
        shortlist = load_shortlist_with_defaults()

        # Find and update the contact
        updated = False
        for entry in shortlist:
            if entry.get("name") == contact_name:
                entry["status"] = status
                entry["comments"] = comments
                entry["last_updated"] = datetime.now().isoformat()
                updated = True
                break

        if not updated:
            return True, f"Error: Contact '{contact_name}' not found", no_update, no_update, no_update

        # Get the last_updated timestamp that was set
        last_updated = None
        for entry in shortlist:
            if entry.get("name") == contact_name:
                last_updated = entry.get("last_updated")
                break

        save_shortlist(shortlist)
        save_to_crm_archive(contact_name, status, comments, last_updated)

        row_data = shortlist_to_row_data(shortlist)
        stats_items = create_stats_items(shortlist)

        return True, f"Saved changes for {contact_name}", row_data, stats_items, row_data

    @app.callback(
        Output("shortlist-crm-table", "rowData", allow_duplicate=True),
        [Input("shortlist-status-filter", "value")],
        [State("shortlist-store-full", "data")],
        prevent_initial_call=True
    )
    def filter_by_status(status_filter, full_data):
        """Filter the displayed data based on status selection."""
        if not full_data:
            return []

        if status_filter == "all":
            return full_data

        return [row for row in full_data if row.get("status") == status_filter]

    @app.callback(
        Output("shortlist-message-history", "children"),
        [Input("shortlist-crm-table", "selectedRows")],
        prevent_initial_call=True
    )
    def display_message_history(selected_rows):
        """Display message history when a contact is selected."""
        if not selected_rows or len(selected_rows) == 0:
            return [html.P("Select a contact to view message history", className="text-muted")]

        contact_name = selected_rows[0].get("name", "")
        if not contact_name:
            return [html.P("Select a contact to view message history", className="text-muted")]

        messages_df = data.get('messages')
        profile_df = data.get('profile')

        return get_message_history_display(contact_name, messages_df, profile_df)

    @app.callback(
        Output("shortlist-selected-index", "data"),
        [Input("shortlist-crm-table", "selectedRows")],
        [State("shortlist-crm-table", "rowData")],
        prevent_initial_call=True
    )
    def track_selected_index(selected_rows, row_data):
        """Track the index of the currently selected row."""
        if not selected_rows or not row_data:
            return None
        selected_name = selected_rows[0].get("name")
        for i, row in enumerate(row_data):
            if row.get("name") == selected_name:
                return i
        return None

    @app.callback(
        Output("shortlist-crm-table", "selectedRows", allow_duplicate=True),
        [Input("keyboard-event", "data")],
        [State("shortlist-selected-index", "data"),
         State("shortlist-crm-table", "rowData")],
        prevent_initial_call=True
    )
    def handle_keyboard_navigation(keyboard_event, current_index, row_data):
        """Handle arrow key navigation in the grid."""
        from dash import no_update

        if not keyboard_event or not keyboard_event.get("key"):
            return no_update

        key = keyboard_event.get("key")
        if key not in ("ArrowUp", "ArrowDown"):
            return no_update

        if not row_data:
            return no_update

        # If no selection, start at first row for down, last for up
        if current_index is None:
            if key == "ArrowDown":
                return [row_data[0]]
            else:
                return [row_data[-1]]

        # Calculate new index
        if key == "ArrowUp":
            new_index = max(0, current_index - 1)
        else:
            new_index = min(len(row_data) - 1, current_index + 1)

        return [row_data[new_index]]

    @app.callback(
        [Output("shortlist-save-toast", "is_open", allow_duplicate=True),
         Output("shortlist-save-toast", "children", allow_duplicate=True),
         Output("shortlist-crm-table", "rowData", allow_duplicate=True),
         Output("shortlist-stats", "children", allow_duplicate=True),
         Output("shortlist-store-full", "data", allow_duplicate=True),
         Output("shortlist-status-dropdown", "value", allow_duplicate=True)],
        [Input("keyboard-event", "data")],
        [State("selected-shortlist-contact", "data"),
         State("shortlist-comments-textarea", "value")],
        prevent_initial_call=True
    )
    def handle_keyboard_status_change(keyboard_event, selected_contact, comments):
        """Handle number key status changes (1-8)."""
        from dash import no_update

        if not keyboard_event or not keyboard_event.get("key"):
            return no_update, no_update, no_update, no_update, no_update, no_update

        key = keyboard_event.get("key")
        if key not in STATUS_KEY_MAP:
            return no_update, no_update, no_update, no_update, no_update, no_update

        if not selected_contact:
            return no_update, no_update, no_update, no_update, no_update, no_update

        contact_name = selected_contact.get("name")
        if not contact_name:
            return no_update, no_update, no_update, no_update, no_update, no_update

        new_status = STATUS_KEY_MAP[key]
        status_label = STATUS_LABELS.get(new_status, new_status)

        # Load current shortlist
        shortlist = load_shortlist_with_defaults()

        # Find and update the contact
        updated = False
        for entry in shortlist:
            if entry.get("name") == contact_name:
                entry["status"] = new_status
                if comments:
                    entry["comments"] = comments
                entry["last_updated"] = datetime.now().isoformat()
                updated = True
                break

        if not updated:
            return True, f"Contact '{contact_name}' not found", no_update, no_update, no_update, no_update

        # Get the last_updated timestamp and comments that were set
        last_updated = None
        final_comments = comments or ''
        for entry in shortlist:
            if entry.get("name") == contact_name:
                last_updated = entry.get("last_updated")
                final_comments = entry.get("comments", '')
                break

        save_shortlist(shortlist)
        save_to_crm_archive(contact_name, new_status, final_comments, last_updated)

        row_data = shortlist_to_row_data(shortlist)
        stats_items = create_stats_items(shortlist)

        return True, f"{contact_name} → {status_label}", row_data, stats_items, row_data, new_status
