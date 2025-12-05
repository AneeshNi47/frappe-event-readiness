app_name = "psn_custom_rdb_app"
app_title = "PSN Readiness Dashboard"
app_publisher = "PSN"
app_description = "PSN Events Readiness Dashboard"
app_email = "me@aneeshbharath.com"
app_license = "mit"

fixtures = [

    # Custom fields like sector, is_sector_lead etc.
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", ["User", "Event Task"]]
        ]
    },

    # Custom Role for this system
    {
        "doctype": "Role",
        "filters": [["name", "=", "Event Readiness Role"]]
    },

    # Permissions assigned to this role
    {
        "doctype": "DocPerm",
        "filters": [["role", "=", "Event Readiness Role"]]
    },

    # Workspace menu
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "Event Readiness Dashboard"]]
    },

    # UI custom script
    {
        "doctype": "Client Script",
        "filters": [["name", "=", "Event UI Customization"]]
    },

    # If you modified core doctypes via Customize Form
    {
        "doctype": "Property Setter",
        "filters": [["doc_type", "in", ["Event Task", "User", "Event Readiness"]]]
    }
]

doc_events = {
    "Event Readiness": {
        "after_insert": "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.create_default_event_tasks"
    },
    "Event Task": {
        "on_update": "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.update_task_weightage"
    }
}

permission_query_conditions = {
    "Event Task": "psn_custom_rdb_app.psn_readiness_dashboard.doctype.event_task.event_task.get_permission_query_conditions"
}

has_permission = {
    "Event Task": "psn_custom_rdb_app.psn_readiness_dashboard.doctype.event_task.event_task.has_permission"
}
