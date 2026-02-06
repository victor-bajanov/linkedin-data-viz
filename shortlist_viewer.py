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
from datetime import datetime, timedelta

# Constants
SHORTLIST_PATH = 'connections_shortlist.json'
CRM_ARCHIVE_PATH = 'crm_archive.json'

STATUS_OPTIONS = [
    {"label": "New", "value": "new"},
    {"label": "On Hold", "value": "on_hold"},
    {"label": "To Contact", "value": "to_contact"},
    {"label": "Contacted", "value": "contacted"},
    {"label": "Meeting Scheduled", "value": "meeting_scheduled"},
    {"label": "In Conversation", "value": "in_conversation"},
    {"label": "Follow Up", "value": "follow_up"},
    {"label": "Proposal Sent", "value": "proposal_sent"},
    {"label": "Closed (Positive)", "value": "closed_positive"},
    {"label": "Closed (Negative)", "value": "closed_negative"},
    {"label": "Closed (Potential Referrer)", "value": "closed_referrer"},
]

STATUS_COLORS = {
    "new": "secondary",
    "on_hold": "dark",
    "to_contact": "info",
    "contacted": "primary",
    "meeting_scheduled": "success",
    "in_conversation": "warning",
    "follow_up": "secondary",
    "proposal_sent": "info",
    "closed_positive": "success",
    "closed_negative": "danger",
    "closed_referrer": "dark",
}

STATUS_LABELS = {opt["value"]: opt["label"] for opt in STATUS_OPTIONS}


def has_data(df):
    """Check if a DataFrame has data (not None and not empty)."""
    return df is not None and not df.empty


def sort_follow_up_rows(rows):
    """Sort follow-up rows by follow_up_sort_key (soonest first) among themselves.

    Non-follow-up rows stay in their original positions. Follow-up rows with
    a real date are reordered into the slots they occupied, sorted ascending.
    """
    fu_indices = []
    fu_rows = []
    for i, row in enumerate(rows):
        if row.get("status") == "follow_up" and row.get("follow_up_sort_key", 9999) != 9999:
            fu_indices.append(i)
            fu_rows.append(row)

    fu_rows.sort(key=lambda r: r.get("follow_up_sort_key", 9999))

    for j, idx in enumerate(fu_indices):
        rows[idx] = fu_rows[j]

    return rows


def shortlist_to_row_data(shortlist):
    """Convert shortlist entries to AG Grid row data format."""
    today = datetime.now().date()
    rows = []
    for entry in shortlist:
        status = entry.get("status", "new")
        label = STATUS_LABELS.get(status, "New")
        follow_up_date = entry.get("follow_up_date")
        follow_up_sort_key = 9999  # default: sort non-follow-up to bottom

        if status == "follow_up" and follow_up_date:
            label = f"Follow Up ({follow_up_date})"
            try:
                fu_date = datetime.strptime(follow_up_date, "%Y-%m-%d").date()
                follow_up_sort_key = (fu_date - today).days
            except ValueError:
                pass

        rows.append({
            "name": entry.get("name", ""),
            "company": entry.get("company", ""),
            "position": entry.get("position", ""),
            "status": status,
            "status_label": label,
            "connected_on": entry.get("connected_on", ""),
            "profile_url": entry.get("profile_url", ""),
            "email": entry.get("email", ""),
            "comments": entry.get("comments", ""),
            "follow_up_date": follow_up_date,
            "follow_up_sort_key": follow_up_sort_key,
        })
    return sort_follow_up_rows(rows)


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
        if 'follow_up_date' not in entry:
            entry['follow_up_date'] = None

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


def save_to_crm_archive(name, status, comments, last_updated, follow_up_date=None):
    """Save CRM data for a contact to the archive."""
    archive = load_crm_archive()
    archive[name] = {
        'status': status,
        'comments': comments,
        'last_updated': last_updated,
        'follow_up_date': follow_up_date
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
            'last_updated': data.get('last_updated'),
            'follow_up_date': data.get('follow_up_date')
        }
    return {'status': 'new', 'comments': '', 'last_updated': None, 'follow_up_date': None}


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
                        dbc.DropdownMenu(
                            label="Filter Status",
                            id="status-filter-dropdown",
                            children=[
                                dbc.DropdownMenuItem(
                                    dbc.Button("Select All", id="status-filter-select-all", size="sm", color="link", className="p-0"),
                                    toggle=False
                                ),
                                dbc.DropdownMenuItem(
                                    dbc.Button("Clear All", id="status-filter-clear-all", size="sm", color="link", className="p-0"),
                                    toggle=False
                                ),
                                dbc.DropdownMenuItem(divider=True),
                                dbc.Checklist(
                                    id="shortlist-status-filter",
                                    options=STATUS_OPTIONS,
                                    value=[opt["value"] for opt in STATUS_OPTIONS],
                                    className="px-3",
                                ),
                            ],
                            size="sm",
                            className="d-inline-block ms-3",
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
                                    "filter": False,
                                    "comparator": {"function": """
                                        function(a, b, nodeA, nodeB, isDescending) {
                                            var keyA = nodeA.data.follow_up_sort_key;
                                            var keyB = nodeB.data.follow_up_sort_key;
                                            if (keyA !== keyB) return keyA - keyB;
                                            return a < b ? -1 : (a > b ? 1 : 0);
                                        }
                                    """},
                                    "cellStyle": {"function": """
                                        function(params) {
                                            if (params.data.status !== 'follow_up' || params.data.follow_up_sort_key === 9999) {
                                                return null;
                                            }
                                            var days = params.data.follow_up_sort_key;
                                            var r, g, b, a;
                                            if (days <= 0) {
                                                r=220; g=53; b=69; a=0.25;
                                            } else if (days <= 3) {
                                                r=255; g=140; b=0; a=0.22;
                                            } else if (days <= 7) {
                                                r=255; g=193; b=7; a=0.20;
                                            } else if (days <= 14) {
                                                r=255; g=193; b=7; a=0.10;
                                            } else {
                                                r=108; g=117; b=125; a=0.06;
                                            }
                                            return {backgroundColor: 'rgba('+r+','+g+','+b+','+a+')'};
                                        }
                                    """},
                                },
                            ],
                            defaultColDef={"resizable": True, "minWidth": 80},
                            dashGridOptions={
                                "rowSelection": "single",
                                "animateRows": True,
                                "postSortRows": {"function": """
                                    function(params) {
                                        var nodes = params.nodes;
                                        var fuIndices = [];
                                        var fuNodes = [];
                                        for (var i = 0; i < nodes.length; i++) {
                                            if (nodes[i].data && nodes[i].data.status === 'follow_up' && nodes[i].data.follow_up_sort_key !== 9999) {
                                                fuIndices.push(i);
                                                fuNodes.push(nodes[i]);
                                            }
                                        }
                                        fuNodes.sort(function(a, b) {
                                            return a.data.follow_up_sort_key - b.data.follow_up_sort_key;
                                        });
                                        for (var j = 0; j < fuIndices.length; j++) {
                                            nodes[fuIndices[j]] = fuNodes[j];
                                        }
                                    }
                                """},
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

                            dbc.Label("Follow-up Date", className="fw-bold", id="follow-up-date-label"),
                            html.Div(
                                dcc.DatePickerSingle(
                                    id="shortlist-follow-up-date",
                                    placeholder="Select date",
                                    display_format="YYYY-MM-DD",
                                    disabled=True,
                                ),
                                className="mb-3",
                                style={"fontSize": "0.875rem"}
                            ),

                            dbc.Label("Comments", className="fw-bold"),
                            dbc.Textarea(
                                id="shortlist-comments-textarea",
                                placeholder="Add notes about this contact...",
                                style={"height": "100px"},
                                disabled=True,
                                className="mb-3"
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

        # Auto-save stores and interval
        dcc.Store(id='contact-loaded-values', data=None),
        dcc.Store(id='comments-pending', data=None),
        dcc.Store(id='comments-debounced', data=None),
        dcc.Interval(id='comments-debounce-check', interval=200, disabled=True),

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

    # Status values mapped to number keys 1-9 and letter shortcuts
    STATUS_KEY_MAP = {
        '1': 'new',
        '2': 'on_hold',
        '3': 'to_contact',
        '4': 'contacted',
        '5': 'meeting_scheduled',
        '6': 'in_conversation',
        '7': 'follow_up',
        '8': 'proposal_sent',
        '9': 'closed_positive',
        '0': 'closed_negative',
        # Letter shortcuts
        'c': 'contacted',
        'h': 'on_hold',
        'x': 'to_contact',
        't': 'in_conversation',
        's': 'meeting_scheduled',
        'f': 'follow_up',
        'p': 'proposal_sent',
        'r': 'closed_referrer',
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

                // Follow-up mode state for f + digits
                window._shortlistFollowUpMode = false;
                window._shortlistFollowUpBuffer = '';
                window._shortlistFollowUpTimeout = null;

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

                    const key = e.key;
                    const letterShortcuts = ['c', 'h', 'x', 't', 's', 'f', 'p', 'r', 'd'];
                    const isLetter = letterShortcuts.includes(key.toLowerCase());

                    // Handle 'd' key for date picker focus
                    if (key.toLowerCase() === 'd') {
                        e.preventDefault();
                        const datePicker = document.getElementById('shortlist-follow-up-date');
                        if (datePicker) {
                            const input = datePicker.querySelector('input');
                            if (input && !input.disabled) {
                                input.focus();
                                input.click();
                            }
                        }
                        return;
                    }

                    // Handle follow-up mode (f + digits)
                    if (window._shortlistFollowUpMode) {
                        // In follow-up mode, accumulate digits
                        if (key >= '0' && key <= '9') {
                            e.preventDefault();
                            window._shortlistFollowUpBuffer += key;
                            // Reset timeout
                            if (window._shortlistFollowUpTimeout) {
                                clearTimeout(window._shortlistFollowUpTimeout);
                            }
                            window._shortlistFollowUpTimeout = setTimeout(function() {
                                // Emit f + buffer
                                window._shortlistPendingKey = 'f' + window._shortlistFollowUpBuffer;
                                window._shortlistKeyTimestamp = Date.now();
                                window._shortlistFollowUpMode = false;
                                window._shortlistFollowUpBuffer = '';
                            }, 500);
                            return;
                        } else if (key === 'Enter') {
                            // Enter ends follow-up mode immediately
                            e.preventDefault();
                            if (window._shortlistFollowUpTimeout) {
                                clearTimeout(window._shortlistFollowUpTimeout);
                            }
                            window._shortlistPendingKey = 'f' + window._shortlistFollowUpBuffer;
                            window._shortlistKeyTimestamp = Date.now();
                            window._shortlistFollowUpMode = false;
                            window._shortlistFollowUpBuffer = '';
                            return;
                        } else {
                            // Non-digit key ends follow-up mode
                            if (window._shortlistFollowUpTimeout) {
                                clearTimeout(window._shortlistFollowUpTimeout);
                            }
                            window._shortlistPendingKey = 'f' + window._shortlistFollowUpBuffer;
                            window._shortlistKeyTimestamp = Date.now();
                            window._shortlistFollowUpMode = false;
                            window._shortlistFollowUpBuffer = '';
                            // Don't return - continue to process the new key
                        }
                    }

                    // Handle 'f' key - enter follow-up mode
                    if (key.toLowerCase() === 'f') {
                        e.preventDefault();
                        window._shortlistFollowUpMode = true;
                        window._shortlistFollowUpBuffer = '';
                        // Set timeout to emit 'f' alone if no digits follow
                        window._shortlistFollowUpTimeout = setTimeout(function() {
                            window._shortlistPendingKey = 'f';
                            window._shortlistKeyTimestamp = Date.now();
                            window._shortlistFollowUpMode = false;
                            window._shortlistFollowUpBuffer = '';
                        }, 500);
                        return;
                    }

                    // Handle arrow keys, number keys 0-9, and other letter shortcuts
                    const otherLetters = ['c', 'h', 'x', 't', 's', 'p', 'r'];
                    const isOtherLetter = otherLetters.includes(key.toLowerCase());
                    if (key === 'ArrowUp' || key === 'ArrowDown' || (key >= '0' && key <= '9') || isOtherLetter) {
                        e.preventDefault();
                        // Lowercase letter shortcuts for consistent matching
                        window._shortlistPendingKey = isOtherLetter ? key.toLowerCase() : key;
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

    # Clientside callback A: On textarea change, record pending edit + enable interval
    app.clientside_callback(
        """
        function(value) {
            if (value === undefined || value === null) {
                return [window.dash_clientside.no_update, window.dash_clientside.no_update];
            }
            return [{value: value, ts: Date.now()}, false];
        }
        """,
        [Output('comments-pending', 'data'),
         Output('comments-debounce-check', 'disabled')],
        [Input('shortlist-comments-textarea', 'value')],
        prevent_initial_call=True
    )

    # Clientside callback B: On interval tick, check if 500ms elapsed
    app.clientside_callback(
        """
        function(n_intervals, pending) {
            if (!pending || !pending.ts) {
                return [window.dash_clientside.no_update, true];
            }
            var elapsed = Date.now() - pending.ts;
            if (elapsed >= 500) {
                return [{value: pending.value, ts: pending.ts}, true];
            }
            return [window.dash_clientside.no_update, window.dash_clientside.no_update];
        }
        """,
        [Output('comments-debounced', 'data'),
         Output('comments-debounce-check', 'disabled', allow_duplicate=True)],
        [Input('comments-debounce-check', 'n_intervals')],
        [State('comments-pending', 'data')],
        prevent_initial_call=True
    )

    @app.callback(
        [Output("shortlist-contact-info", "children"),
         Output("shortlist-contact-name", "children"),
         Output("shortlist-status-dropdown", "value"),
         Output("shortlist-status-dropdown", "disabled"),
         Output("shortlist-comments-textarea", "value"),
         Output("shortlist-comments-textarea", "disabled"),
         Output("selected-shortlist-contact", "data"),
         Output("shortlist-follow-up-date", "date"),
         Output("shortlist-follow-up-date", "disabled"),
         Output("contact-loaded-values", "data"),
         Output("comments-pending", "data", allow_duplicate=True),
         Output("comments-debounced", "data", allow_duplicate=True),
         Output("comments-debounce-check", "disabled", allow_duplicate=True)],
        [Input("shortlist-crm-table", "selectedRows")],
        [State("shortlist-status-dropdown", "value"),
         State("shortlist-comments-textarea", "value"),
         State("shortlist-follow-up-date", "date"),
         State("contact-loaded-values", "data"),
         State("selected-shortlist-contact", "data")],
        prevent_initial_call=True
    )
    def display_contact_details(selected_rows, prev_status, prev_comments, prev_follow_up_date, loaded_values, prev_selected):
        """Display details when a contact is selected. Flushes unsaved changes for previous contact."""
        from dash import no_update

        # Flush unsaved changes for previous contact before switching
        if loaded_values and prev_selected and prev_selected.get("name"):
            prev_name = prev_selected["name"]
            changed = False
            if prev_status != loaded_values.get("status"):
                changed = True
            if (prev_comments or "") != (loaded_values.get("comments") or ""):
                changed = True
            if prev_follow_up_date != loaded_values.get("follow_up_date"):
                changed = True

            if changed:
                shortlist = load_shortlist_with_defaults()
                flush_follow_up = prev_follow_up_date
                if prev_status != "follow_up":
                    flush_follow_up = None
                for entry in shortlist:
                    if entry.get("name") == prev_name:
                        entry["status"] = prev_status
                        entry["comments"] = prev_comments or ""
                        entry["last_updated"] = datetime.now().isoformat()
                        entry["follow_up_date"] = flush_follow_up
                        break
                save_shortlist(shortlist)
                save_to_crm_archive(prev_name, prev_status, prev_comments or "", datetime.now().isoformat(), flush_follow_up)

        if not selected_rows or len(selected_rows) == 0:
            return (
                [html.P("Select a contact from the list to view details", className="text-muted")],
                "Contact Details",
                "new",
                True,
                "",
                True,
                None,
                None,
                True,
                None,
                None, None, True
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
        follow_up_date = contact.get("follow_up_date")

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

        # Date picker is enabled only when status is follow_up
        date_picker_disabled = status != "follow_up"

        loaded = {"status": status, "comments": comments or "", "follow_up_date": follow_up_date}

        return (
            info_items,
            name,
            status,
            False,
            comments or "",
            False,
            {"name": name},
            follow_up_date,
            date_picker_disabled,
            loaded,
            None, None, True
        )

    @app.callback(
        [Output("shortlist-save-toast", "is_open"),
         Output("shortlist-save-toast", "children"),
         Output("shortlist-crm-table", "rowData"),
         Output("shortlist-stats", "children"),
         Output("shortlist-store-full", "data"),
         Output("contact-loaded-values", "data", allow_duplicate=True)],
        [Input("shortlist-status-dropdown", "value"),
         Input("shortlist-follow-up-date", "date"),
         Input("comments-debounced", "data")],
        [State("selected-shortlist-contact", "data"),
         State("contact-loaded-values", "data"),
         State("shortlist-status-filter", "value"),
         State("shortlist-comments-textarea", "value")],
        prevent_initial_call=True
    )
    def auto_save_contact(status, follow_up_date, comments_debounced, selected_contact, loaded_values, status_filter, comments_textarea):
        """Auto-save changes when status, follow-up date, or comments change."""
        from dash import no_update

        if not selected_contact or not loaded_values:
            return no_update, no_update, no_update, no_update, no_update, no_update

        contact_name = selected_contact.get("name")
        if not contact_name:
            return no_update, no_update, no_update, no_update, no_update, no_update

        # Determine current values
        current_status = status
        current_comments = comments_textarea or ""
        current_follow_up = follow_up_date

        # Only use debounced comments when the debounce timer is the actual trigger.
        # Otherwise the store holds stale data from a previous contact.
        if ctx.triggered_id == "comments-debounced" and comments_debounced and comments_debounced.get("value") is not None:
            current_comments = comments_debounced["value"]

        # Compare against loaded values - skip if nothing changed
        loaded_status = loaded_values.get("status")
        loaded_comments = loaded_values.get("comments") or ""
        loaded_follow_up = loaded_values.get("follow_up_date")

        if current_status == loaded_status and current_comments == loaded_comments and current_follow_up == loaded_follow_up:
            return no_update, no_update, no_update, no_update, no_update, no_update

        # Clear follow_up_date if status is not follow_up
        if current_status != "follow_up":
            current_follow_up = None

        # Load current shortlist
        shortlist = load_shortlist_with_defaults()

        # Find and update the contact
        updated = False
        for entry in shortlist:
            if entry.get("name") == contact_name:
                entry["status"] = current_status
                entry["comments"] = current_comments
                entry["last_updated"] = datetime.now().isoformat()
                entry["follow_up_date"] = current_follow_up
                updated = True
                break

        if not updated:
            return no_update, no_update, no_update, no_update, no_update, no_update

        last_updated = datetime.now().isoformat()
        save_shortlist(shortlist)
        save_to_crm_archive(contact_name, current_status, current_comments, last_updated, current_follow_up)

        row_data = shortlist_to_row_data(shortlist)
        stats_items = create_stats_items(shortlist)

        # Apply current status filter to displayed data
        filtered_data = row_data
        if status_filter:
            filtered_data = sort_follow_up_rows([row for row in row_data if row.get("status") in status_filter])

        new_loaded = {"status": current_status, "comments": current_comments, "follow_up_date": current_follow_up}

        return True, f"Auto-saved {contact_name}", filtered_data, stats_items, row_data, new_loaded

    @app.callback(
        Output("shortlist-follow-up-date", "disabled", allow_duplicate=True),
        [Input("shortlist-status-dropdown", "value")],
        prevent_initial_call=True
    )
    def toggle_date_picker_on_status_change(status):
        """Enable/disable date picker based on status dropdown value."""
        return status != "follow_up"

    @app.callback(
        Output("shortlist-crm-table", "rowData", allow_duplicate=True),
        [Input("shortlist-status-filter", "value")],
        [State("shortlist-store-full", "data")],
        prevent_initial_call=True
    )
    def filter_by_status(selected_statuses, full_data):
        """Filter the displayed data based on selected statuses (multi-select)."""
        if not full_data:
            return []

        if not selected_statuses:
            return []

        return sort_follow_up_rows([row for row in full_data if row.get("status") in selected_statuses])

    @app.callback(
        Output("shortlist-status-filter", "value"),
        [Input("status-filter-select-all", "n_clicks"),
         Input("status-filter-clear-all", "n_clicks")],
        prevent_initial_call=True
    )
    def handle_select_all_clear(select_all, clear_all):
        """Handle Select All / Clear All buttons for status filter."""
        from dash import no_update
        trigger_id = ctx.triggered_id
        if trigger_id == "status-filter-select-all":
            return [opt["value"] for opt in STATUS_OPTIONS]
        elif trigger_id == "status-filter-clear-all":
            return []
        return no_update

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
         Output("shortlist-status-dropdown", "value", allow_duplicate=True),
         Output("shortlist-follow-up-date", "date", allow_duplicate=True),
         Output("shortlist-follow-up-date", "disabled", allow_duplicate=True),
         Output("contact-loaded-values", "data", allow_duplicate=True)],
        [Input("keyboard-event", "data")],
        [State("selected-shortlist-contact", "data"),
         State("shortlist-comments-textarea", "value"),
         State("shortlist-status-filter", "value")],
        prevent_initial_call=True
    )
    def handle_keyboard_status_change(keyboard_event, selected_contact, comments, status_filter):
        """Handle number key and letter status changes, including f + digits for follow-up."""
        from dash import no_update

        NO_UPD = (no_update,) * 9

        if not keyboard_event or not keyboard_event.get("key"):
            return NO_UPD

        key = keyboard_event.get("key")

        # Parse follow-up key with optional day offset (e.g., 'f', 'f5', 'f20')
        follow_up_date = None
        day_offset = 0
        if key.startswith('f'):
            if key == 'f':
                # f alone means follow_up with today's date
                day_offset = 0
            else:
                # f + digits (e.g., f5, f20)
                try:
                    day_offset = int(key[1:])
                except ValueError:
                    return NO_UPD

            new_status = 'follow_up'
            follow_up_date = (datetime.now() + timedelta(days=day_offset)).strftime('%Y-%m-%d')
        elif key in STATUS_KEY_MAP:
            new_status = STATUS_KEY_MAP[key]
        else:
            return NO_UPD

        if not selected_contact:
            return NO_UPD

        contact_name = selected_contact.get("name")
        if not contact_name:
            return NO_UPD

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
                # Set follow_up_date if status is follow_up, clear otherwise
                if new_status == 'follow_up':
                    entry["follow_up_date"] = follow_up_date
                else:
                    entry["follow_up_date"] = None
                updated = True
                break

        if not updated:
            return True, f"Contact '{contact_name}' not found", no_update, no_update, no_update, no_update, no_update, no_update, no_update

        # Get the last_updated timestamp and comments that were set
        last_updated = None
        final_comments = comments or ''
        final_follow_up_date = None
        for entry in shortlist:
            if entry.get("name") == contact_name:
                last_updated = entry.get("last_updated")
                final_comments = entry.get("comments", '')
                final_follow_up_date = entry.get("follow_up_date")
                break

        save_shortlist(shortlist)
        save_to_crm_archive(contact_name, new_status, final_comments, last_updated, final_follow_up_date)

        row_data = shortlist_to_row_data(shortlist)
        stats_items = create_stats_items(shortlist)

        # Apply current status filter to displayed data
        filtered_data = row_data
        if status_filter:
            filtered_data = sort_follow_up_rows([row for row in row_data if row.get("status") in status_filter])

        # Build toast message
        toast_msg = f"{contact_name} → {status_label}"
        if new_status == 'follow_up' and follow_up_date:
            toast_msg += f" ({follow_up_date})"

        # Date picker enabled only for follow_up status
        date_picker_disabled = new_status != 'follow_up'

        # Update loaded values so auto-save doesn't double-fire
        new_loaded = {"status": new_status, "comments": final_comments, "follow_up_date": final_follow_up_date}

        return True, toast_msg, filtered_data, stats_items, row_data, new_status, final_follow_up_date, date_picker_disabled, new_loaded
