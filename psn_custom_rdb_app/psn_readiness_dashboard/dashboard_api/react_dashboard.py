import frappe


@frappe.whitelist()
def get_admin_dashboard_summary():
    """
    Returns dashboard KPIs.

    - Administrator → sees ALL events and ALL tasks (global dashboard)
    - Other users  → sees ONLY tasks where they are the 'incharge'
    """
    user = frappe.session.user
    total_events = frappe.db.count("Event Readiness")
    task_filters = {}

    if user != "Administrator":
        task_filters["incharge"] = user

    tasks = frappe.get_all(
        "Event Task",
        filters=task_filters,
        fields=["status", "progress"]
    )

    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t.status == "Completed")
    in_progress = sum(1 for t in tasks if t.status == "In Progress")
    pending = sum(1 for t in tasks if t.status == "Pending")
    delayed = sum(1 for t in tasks if t.status == "Delayed")

    if total_tasks > 0:
        global_readiness = int((completed / total_tasks) * 100)
    else:
        global_readiness = 0

    # -----------------------------
    # 5️⃣ Response
    # -----------------------------
    return {
        "user": user,
        "total_events": total_events,
        "total_tasks": total_tasks,
        "completed_tasks": completed,
        "in_progress_tasks": in_progress,
        "pending_tasks": pending,
        "delayed_tasks": delayed,
        "global_readiness": global_readiness
    }


@frappe.whitelist()
def get_active_events_summary():
    """
    Returns event-wise readiness stats.
    Useful for 'Active Events' tiles in the React Admin UI.
    """
    events = frappe.get_all(
        "Event Readiness",
        fields=[
            "name", "event_name", "event_readiness",
            "event_date", "custom_event_end_date", "total_tasks", "completed_tasks",
            "pending_tasks", "custom_in_progress_tasks",
            "delayed_tasks"
        ],
        order_by="creation asc"
    )
    return events
