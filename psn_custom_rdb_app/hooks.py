app_name = "psn_custom_rdb_app"
app_title = "PSN Readiness Dashboard"
app_publisher = "PSN"
app_description = "PSN Events Readiness Dashboard"
app_email = "me@aneeshbharath.com"
app_license = "mit"


fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            ["dt", "in", ["User", "Event Task", "Event Readiness"]]
        ]
    },
    {
        "doctype": "Role",
        "filters": [["name", "=", "Event Readiness Role"]]
    },
    {
        "doctype": "DocPerm",
        "filters": [["role", "=", "Event Readiness Role"]]
    },
    {
        "doctype": "Workspace",
        "filters": [["name", "=", "Event Readiness Dashboard"]]
    },
    {
        "doctype": "Client Script",
        "filters": [["name", "=", "Event UI Customization"]]
    },
    {
        "doctype": "Property Setter",
        "filters": [
            ["doc_type", "in", ["Event Task", "User", "Event Readiness"]],
            ["property", "in", ["mandatory", "reqd", "options", "hidden"]]
        ]
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
