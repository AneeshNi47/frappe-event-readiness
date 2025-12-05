app_name = "psn_custom_rdb_app"
app_title = "PSN Readiness Dashboard"
app_publisher = "PSN"
app_description = "PSN Events Readiness Dashboard"
app_email = "me@aneeshbharath.com"
app_license = "mit"

fixtures = [
    # Custom fields required by the system
    {
        "doctype": "Custom Field",
        "filters": [
            ["name", "in", [
                # User fields
                "User-sector",
                "User-is_sector_lead",

                # Event Task fields
                "Event Task-sector",
                "Event Task-incharge",

                # Event Readiness fields (if any custom)
                # add only if created
            ]]
        ]
    },

    # Custom Role
    {
        "doctype": "Role",
        "filters": [["name", "=", "Event Readiness Role"]]
    },

    # Permissions for the role
    {
        "doctype": "DocPerm",
        "filters": [["role", "=", "Event Readiness Role"]]
    },

    # Workspace
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "Event Readiness Dashboard"]]
    },

    # UI Script
    {
        "doctype": "Client Script",
        "filters": [["name", "=", "Event UI Customization"]]
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
