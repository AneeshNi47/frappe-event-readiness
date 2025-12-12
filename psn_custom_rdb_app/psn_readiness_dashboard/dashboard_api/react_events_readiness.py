import frappe

frappe.flags.ignore_csrf = True


@frappe.whitelist()
def get_events_for_user():
    user = frappe.session.user

    # -------------------------
    # 1️⃣ Fetch User Sector List
    # -------------------------
    user_sector_list = []
    user_is_lead = False

    kpi_entries = frappe.get_all(
        "User Sector KPI",
        filters={"user": user},
        fields=["sector", "custom_is_sector_lead"]
    )

    if kpi_entries:
        user_sector_list = [entry.sector for entry in kpi_entries]
        user_is_lead = any(
            entry.custom_is_sector_lead for entry in kpi_entries)

    # -------------------------
    # 2️⃣ Administrator → can see ALL events
    # -------------------------
    if user == "Administrator":
        allowed_event_names = None  # None = fetch all
    else:
        # -------------------------
        # 3️⃣ Fetch tasks belonging to user's sectors
        # -------------------------
        if user_sector_list:
            tasks = frappe.get_all(
                "Event Task",
                filters={"sector": ["in", user_sector_list]},
                fields=["event"],
                distinct=True
            )
        else:
            tasks = []

        # Extract event names from tasks
        allowed_event_names = list({t.event for t in tasks if t.event})

    # -------------------------
    # 4️⃣ Build filters for Events
    # -------------------------
    event_filters = {}

    if allowed_event_names is not None:
        # If user has NO tasks in their sectors → return NO events
        if not allowed_event_names:
            return {
                "events": [],
                "user": user,
                "user_sector_list": user_sector_list,
                "user_is_lead": user_is_lead
            }

        event_filters["name"] = ["in", allowed_event_names]

    # -------------------------
    # 5️⃣ Fetch Events
    # -------------------------
    events = frappe.get_all(
        "Event Readiness",
        filters=event_filters,
        fields=[
            "name",
            "event_name",
            "event_date",
            "custom_event_end_date",
            "custom_in_progress_tasks",
            "total_tasks",
            "completed_tasks",
            "delayed_tasks",
            "event_readiness"
        ],
        order_by="event_date asc"
    )

    return {
        "events": events,
        "user": user,
        "user_sector_list": user_sector_list,
        "user_is_lead": user_is_lead
    }


@frappe.whitelist()
def get_event_details(event_name):
    """
    Returns:
      - event detail fields
      - tasks visible to the current user
      - breakdown counts
      - unique sectors
    """

    user = frappe.session.user

    # -------------------------
    # 1️⃣ Fetch Event
    # -------------------------
    event = frappe.get_doc("Event Readiness", event_name)

    # -------------------------
    # 2️⃣ Load User Sector Permissions
    # -------------------------
    user_sector_list = []
    user_is_lead = False

    kpi_entries = frappe.get_all(
        "User Sector KPI",
        filters={"user": user},
        fields=["sector", "custom_is_sector_lead"]
    )

    if kpi_entries:
        user_sector_list = [e.sector for e in kpi_entries]
        user_is_lead = any(e.custom_is_sector_lead for e in kpi_entries)

    # -------------------------
    # 3️⃣ Build task filters
    # -------------------------
    task_filters = {"event": event_name}

    if user != "Administrator":
        if user_is_lead and user_sector_list:
            task_filters["sector"] = ["in", user_sector_list]
        else:
            task_filters["incharge"] = user

    # -------------------------
    # 4️⃣ Fetch tasks for this event
    # -------------------------
    tasks = frappe.get_all(
        "Event Task",
        filters=task_filters,
        fields=[
            "name",
            "l2_task_name",
            "sector",
            "status",
            "incharge",
            "due_date",
            "progress"
        ],
        order_by="creation asc"
    )

    # -------------------------
    # 5️⃣ Build summary counts
    # -------------------------
    total = len(tasks)
    pending = sum(1 for t in tasks if t.status == "Pending")
    in_progress = sum(1 for t in tasks if t.status == "In Progress")
    completed = sum(1 for t in tasks if t.status == "Completed")
    delayed = sum(1 for t in tasks if t.status == "Delayed")

    # Unique sectors
    sectors = sorted({t.sector for t in tasks if t.sector})

    # -------------------------
    # 6️⃣ Response payload
    # -------------------------
    return {
        "event": {
            "name": event.name,
            "event_name": event.event_name,
            "event_date": event.event_date,
            "custom_event_end_date": event.custom_event_end_date,
            "event_readiness": event.event_readiness,
        },
        "tasks": tasks,
        "summary": {
            "total": total,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "delayed": delayed,
        },
        "sectors": sectors,
        "user": user,
        "user_sector_list": user_sector_list,
        "user_is_lead": user_is_lead,
    }


@frappe.whitelist()
def update_event_task_status(task_name, status, delay_reason=None):
    """
    React wrapper for updating task status.
    """
    from psn_custom_rdb_app.psn_readiness_dashboard.event_logic import \
        update_event_task_status as base_update

    return base_update(task_name, status, delay_reason)


@frappe.whitelist()
def update_task_incharge(task_name, user):
    """
    Assign task to a different user.
    """
    from psn_custom_rdb_app.psn_readiness_dashboard.event_logic import \
        update_task_incharge as base_update

    return base_update(task_name, user)


@frappe.whitelist()
def get_task_activity(task_name):
    """
    Get comment/activity log for React UI.
    """
    from psn_custom_rdb_app.psn_readiness_dashboard.event_logic import \
        get_task_activity

    return get_task_activity(task_name)
