app_name = "psn_custom_rdb_app"
app_title = "PSN Readiness Dashboard"
app_publisher = "PSN"
app_description = "PSN Events Readiness Dashboard"
app_email = "me@aneeshbharath.com"
app_license = "mit"

# ------------------------------------------------------------
# FIXTURES — ensure all customisation is portable across systems
# ------------------------------------------------------------
fixtures = [

    # Custom Fields added to core doctypes
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", ["User", "Event Task"]],
            ["name", "like", "%sector%"],
        ]
    },

    # Custom Role for this app
    {
        "doctype": "Role",
        "filters": [["name", "=", "Event Readiness Role"]]
    },

    # Role-based DocPerms
    {
        "doctype": "DocPerm",
        "filters": [["role", "=", "Event Readiness Role"]]
    },

    # Page + Report access for the same role
    {
        "doctype": "Role Permission for Page and Report",
        "filters": [["role", "=", "Event Readiness Role"]]
    },

    # Client scripts for UI logic
    {
        "doctype": "Client Script",
        "filters": [["name", "in", ["Event UI Customization"]]]
    },

    # Workspace/Menu layout
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "Event Readiness Dashboard"]]
    },

    # If you modified any default field via Customize Form
    {
        "doctype": "Property Setter",
        "filters": [
            ["doc_type", "in", ["Event Readiness", "Event Task", "User"]]
        ]
    },

    # Dashboard charts created for this app (optional but recommended)
    {
        "doctype": "Dashboard Chart",
        "filters": [
            ["module", "=", "PSN Readiness Dashboard"]
        ]
    }
]

# ------------------------------------------------------------
# EVENTS — automatic logic triggers
# ------------------------------------------------------------
doc_events = {
    "Event Readiness": {
        "after_insert": "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.create_default_event_tasks"
    },
    "Event Task": {
        "on_update": "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.update_task_weightage"
    }
}

# ------------------------------------------------------------
# PERMISSIONS — Query-level security for Event Task
# ------------------------------------------------------------
permission_query_conditions = {
    "Event Task": "psn_custom_rdb_app.psn_readiness_dashboard.doctype.event_task.event_task.get_permission_query_conditions"
}

has_permission = {
    "Event Task": "psn_custom_rdb_app.psn_readiness_dashboard.doctype.event_task.event_task.has_permission"
}
