app_name = "psn_custom_rdb_app"
app_title = "PSN Readiness Dashboard"
app_publisher = "PSN"
app_description = "PSN Events Readiness Dashboard"
app_email = "saif.alremeithi@psn.gov.ae"
app_license = "mit"

doc_events = {
    "Event Readiness": {
        "after_insert": "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.create_default_event_tasks"
    },
    "Event Task": {
        "on_update": "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.update_task_weightage"
    }
}
