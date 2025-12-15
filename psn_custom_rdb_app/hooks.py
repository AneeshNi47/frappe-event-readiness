app_name = "psn_custom_rdb_app"
app_title = "PSN Readiness Dashboard"
app_publisher = "PSN"
app_description = "PSN Events Readiness Dashboard"
app_email = "me@aneeshbharath.com"
app_license = "mit"

csrf_exempt = [
    "frappe.integrations.oauth2.get_token",
    "frappe.integrations.oauth2.authorize"
]

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["dt", "in", ["Event Task", "Event Readiness",
                          "User Sector KPI", "User Sector Assignment"]]
        ]
    },
    {
        "dt": "DocType",
        "filters": [["name", "=", "User Sector KPI"]]
    },
    {
        "dt": "DocType",
        "filters": [["name", "=", "User Sector Assignment"]]
    },
    {
        "doctype": "Role",
        "filters": [
            ["name", "in", [
                "Event Readiness Role",
                "Sector Member",
                "Sector Lead"
            ]]
        ]
    },
    {
        "doctype": "DocPerm",
        "filters": [
            ["role", "in", [
                "Event Readiness Role",
                "Sector Member",
                "Sector Lead"
            ]]
        ]
    },
    {
        "dt": "Workspace",
        "filters": [["name", "=", "Event Readiness Dashboard"]]
    },
    {
        "dt": "Calendar View",
        "filters": [["reference_doctype", "=", "Event Readiness"]]
    },
    {
        "dt": "Client Script",
        "filters": [[
            "name", "in", [
                "Event UI Customization",
                "Event Readiness Dashboard Script",
                "Event Task UI Enhancements"
            ]
        ]]
    },
    {
        "dt": "Custom HTML Block",
        "filters": [[
            "name", "in", [
                "Create Event",
                "Calendar View"
            ]
        ]]
    },
    {
        "dt": "Report",
        "filters": [[
            "name", "in", [
                "Event Readiness Report"
            ]
        ]]
    },
    {
        "dt": "Report Filter",
        "filters": [[
            "parent", "in", [
                "Event Readiness Summary",
                "Event Task Details"
            ]
        ]]
    }
]

doc_events = {
    "Event Readiness": {
        "after_insert": "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.enqueue_default_event_tasks"
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
