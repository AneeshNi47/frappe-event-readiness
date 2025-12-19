import frappe
from frappe.utils import add_days, getdate, nowdate

frappe.flags.ignore_csrf = True

ALLOWED_SORT_FIELDS = {
    "event_date": "event_date",
    "end_date": "custom_event_end_date",
    "created_on": "creation",
    "event_name": "event_name",
    "readiness": "event_readiness",
}


@frappe.whitelist()
def get_events_for_user(
        sort_by="event_date",
        sort_order="asc"):
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
    if "System Manager" in frappe.get_roles(user):
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

    sort_order = sort_order.lower()
    if sort_order not in ("asc", "desc"):
        sort_order = "asc"
    order_field = ALLOWED_SORT_FIELDS.get(sort_by, "event_date")

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
            "event_readiness",
            "custom_event_sponsor",
            "creation",
            "owner",
        ],
        order_by=f"{order_field} {sort_order}"
    )

    return {
        "events": events,
        "user": user,
        "user_sector_list": user_sector_list,
        "user_is_lead": user_is_lead
    }


@frappe.whitelist()
def get_event_overview(event_name):
    """
    Returns:
      - event detail fields
      - breakdown counts (summary)
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
    # 3️⃣ Build task filters (for summary only)
    # -------------------------
    task_filters = {"event": event_name}

    if user != "Administrator":
        if user_is_lead and user_sector_list:
            task_filters["sector"] = ["in", user_sector_list]
        else:
            task_filters["incharge"] = user

    # -------------------------
    # 4️⃣ Fetch ONLY statuses for summary
    # -------------------------
    task_statuses = frappe.get_all(
        "Event Task",
        filters=task_filters,
        fields=["status"]
    )

    # -------------------------
    # 5️⃣ Build summary counts
    # -------------------------
    total = len(task_statuses)
    pending = sum(1 for t in task_statuses if t.status == "Pending")
    in_progress = sum(1 for t in task_statuses if t.status == "In Progress")
    completed = sum(1 for t in task_statuses if t.status == "Completed")
    delayed = sum(1 for t in task_statuses if t.status == "Delayed")

    # -------------------------
    # 6️⃣ Unique sectors (light query)
    # -------------------------
    sectors = sorted({
        t.sector for t in frappe.get_all(
            "Event Task",
            filters={"event": event_name},
            fields=["sector"]
        ) if t.sector
    })

    # -------------------------
    # 7️⃣ Response payload
    # -------------------------
    return {
        "event": {
            "name": event.name,
            "event_name": event.event_name,
            "event_date": event.event_date,
            "custom_event_end_date": event.custom_event_end_date,
            "event_readiness": event.event_readiness,
        },
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
def get_event_tasks(event_name):
    """
    Returns:
      - tasks visible to the current user
    """

    user = frappe.session.user

    # -------------------------
    # 1️⃣ Load User Sector Permissions
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
    # 2️⃣ Build task filters
    # -------------------------
    task_filters = {"event": event_name}

    if user != "Administrator":
        if user_is_lead and user_sector_list:
            task_filters["sector"] = ["in", user_sector_list]
        else:
            task_filters["incharge"] = user

    # -------------------------
    # 3️⃣ Fetch tasks
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

    return {
        "tasks": tasks
    }


@frappe.whitelist()
def create_event(
    event_name,
    event_date,
    custom_event_end_date,
    custom_event_sponsor,
    event_description,
    use_default_tasks=1
):
    """
    Create a new Event Readiness record
    Called from React application
    """

    user = frappe.session.user

    # -------------------------
    # 1️⃣ Permission Check
    # -------------------------
    if not frappe.has_permission("Event Readiness", "create", user=user):
        frappe.throw(
            "You do not have permission to create events",
            frappe.PermissionError
        )

    # -------------------------
    # 2️⃣ Date Validation
    # -------------------------
    today = getdate(nowdate())
    min_start_date = add_days(today, 1)

    start_date = getdate(event_date)
    end_date = getdate(custom_event_end_date)

    if start_date < min_start_date:
        frappe.throw("Event Start Date must be at least 1 day after today")

    if end_date <= start_date:
        frappe.throw("Event End Date must be greater than Event Start Date")

    # -------------------------
    # 3️⃣ Create Event Document
    # -------------------------
    event = frappe.get_doc({
        "doctype": "Event Readiness",
        "event_name": event_name,
        "event_date": start_date,
        "custom_event_end_date": end_date,
        "event_owner": user,
        "custom_event_sponsor": custom_event_sponsor,
        "event_description": event_description,
        "use_default_tasks": 1 if int(use_default_tasks) else 0
    })

    event.insert(ignore_permissions=False)
    if use_default_tasks:
        event.db_set("custom_tasks_generation_status", "Pending")
    frappe.db.commit()

    return {
        "message": "Event created successfully",
        "event_name": event.name
    }


@frappe.whitelist()
def get_sector_users_for_event(event_name):
    sectors = frappe.get_all(
        "Event Task",
        filters={"event": event_name},
        fields=["sector"],
        distinct=True
    )
    sector_list = [s.sector for s in sectors if s.sector]
    if not sector_list:
        return {}
    entries = frappe.get_all(
        "User Sector KPI",
        filters={"sector": ["in", sector_list]},
        fields=["sector", "user"]
    )
    sector_users = {}
    for e in entries:
        sector_users.setdefault(e.sector, []).append(e.user)
    return sector_users
