import json

import frappe
from frappe.utils import add_days, cint, nowdate

# ======================================================
#  HELPER FUNCTIONS FOR PERMISSIONS
# ======================================================


@frappe.whitelist()
def get_logged_in_user_details():
    user = frappe.session.user

    kpis = frappe.get_all(
        "User Sector KPI",
        filters={"user": user},
        fields=["sector", "custom_is_sector_lead"]
    )

    sectors = [k.sector for k in kpis]
    is_lead = any(k.custom_is_sector_lead for k in kpis)

    return {
        "user": user,
        "full_name": frappe.db.get_value("User", user, "full_name"),
        "sector_list": sectors,
        "is_sector_lead": is_lead,
        "roles": frappe.get_roles(user)
    }


@frappe.whitelist()
def get_event_list():
    return frappe.get_all(
        "Event Readiness",
        fields=[
            "name", "event_name", "event_date",
            "event_readiness", "total_tasks", "pending_tasks",
            "custom_in_progress_tasks", "completed_tasks", "delayed_tasks"
        ],
        order_by="event_date asc"
    )


@frappe.whitelist()
def get_all_tasks_for_user():
    user = frappe.session.user

    # fetch user sectors and lead status
    sector_list = []
    is_lead = False

    kpis = frappe.get_all(
        "User Sector KPI",
        filters={"user": user},
        fields=["sector", "custom_is_sector_lead"]
    )

    if kpis:
        sector_list = [k.sector for k in kpis]
        is_lead = any(k.custom_is_sector_lead for k in kpis)

    filters = {}

    if user == "Administrator":
        pass
    elif is_lead and sector_list:
        filters["sector"] = ["in", sector_list]
    else:
        filters["incharge"] = user

    return frappe.get_all(
        "Event Task",
        filters=filters,
        fields=[
            "name", "event", "l2_task_name", "sector",
            "status", "incharge", "due_date", "progress"
        ],
        order_by="due_date asc"
    )


@frappe.whitelist()
def get_all_events():
    """Return all events with dates for calendar"""
    return frappe.get_all(
        "Event Readiness",
        fields=["name", "event_name", "event_date"]
    )


def is_admin():
    return frappe.session.user == "Administrator"


def get_user_sector():
    return frappe.db.get_value("User", frappe.session.user, "sector")


def is_sector_lead():
    return frappe.db.get_value("User", frappe.session.user, "is_sector_lead") == 1


# ======================================================
#  AUTO CREATE DEFAULT TASKS
# ======================================================

def create_default_event_tasks(doc, method=None):
    if not doc.use_default_tasks:
        return

    templates = frappe.get_all(
        "Task Template",
        fields=["sector", "task_name", "description", "duration_days"]
    )

    for tmpl in templates:

        # avoid duplicates
        if frappe.db.exists("Event Task", {
            "event": doc.name,
            "sector": tmpl.sector,
            "l2_task_name": tmpl.task_name
        }):
            continue

        # get sector lead
        lead = frappe.db.get_value(
            "Sector Member",
            {"is_sector_lead": 1, "parent": tmpl.sector},
            "user"
        )

        task = frappe.new_doc("Event Task")
        task.event = doc.name
        task.sector = tmpl.sector
        task.sector_lead = lead
        task.l2_task_name = tmpl.task_name
        task.task_description = tmpl.description
        task.status = "Pending"
        task.weightage = 0
        task.progress = 0

        base_date = doc.event_date or nowdate()
        task.due_date = add_days(base_date, tmpl.duration_days or 0)

        task.insert(ignore_permissions=True)

    update_event_task_stats(doc.name)
    frappe.msgprint("Default tasks added.")


# ======================================================
#  UPDATE WEIGHTAGE & RECALCULATE READINESS
# ======================================================

def update_task_weightage(doc, method=None):
    weightage_map = {
        "Pending": 0,
        "Delayed": 0,
        "In Progress": 50,
        "Completed": 100
    }

    doc.weightage = weightage_map.get(doc.status, 0)
    doc.progress = doc.weightage

    update_event_task_stats(doc.event)


# ======================================================
#  RECALCULATE METRICS FOR EVENT READINESS
# ======================================================

def update_event_task_stats(event_name):
    tasks = frappe.get_all(
        "Event Task",
        filters={"event": event_name},
        fields=["status"]
    )

    total = len(tasks)
    pending = sum(1 for t in tasks if t.status == "Pending")
    in_progress = sum(1 for t in tasks if t.status == "In Progress")
    completed = sum(1 for t in tasks if t.status == "Completed")
    delayed = sum(1 for t in tasks if t.status == "Delayed")

    readiness = int((completed / total) * 100) if total else 0

    frappe.db.set_value("Event Readiness", event_name, {
        "total_tasks": total,
        "pending_tasks": pending,
        "custom_in_progress_tasks": in_progress,
        "completed_tasks": completed,
        "delayed_tasks": delayed,
        "event_readiness": readiness,
    })
    frappe.db.commit()


# ======================================================
#  FILTERED TASK LIST FOR CLIENT-SIDE UI
# ======================================================
@frappe.whitelist()
def get_tasks_for_event(event_name):
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
    # 2️⃣ Build Base Filters
    # -------------------------
    filters = {"event": event_name}

    if user != "Administrator":
        if user_is_lead and user_sector_list:
            # Sector lead sees tasks from ALL assigned sectors
            filters["sector"] = ["in", user_sector_list]
        else:
            # Regular user sees only assigned tasks
            filters["incharge"] = user

    # -------------------------
    # 3️⃣ Fetch Event Tasks
    # -------------------------
    tasks = frappe.get_all(
        "Event Task",
        filters=filters,
        fields=[
            "name", "l2_task_name", "sector", "status",
            "incharge", "creation", "due_date", "progress"
        ],
        order_by="creation asc"
    )

    # -------------------------
    # 4️⃣ Sector-wise User Map
    # for ADMIN or SECTOR LEAD
    # -------------------------
    sector_users = {}

    if user == "Administrator" or user_is_lead:
        relevant_sectors = list({t.sector for t in tasks if t.sector})

        if relevant_sectors:
            members = frappe.get_all(
                "Sector Member",
                filters={"parent": ["in", relevant_sectors]},
                fields=["parent as sector", "user", "is_sector_lead"]
            )

            for m in members:
                sector_users.setdefault(m.sector, []).append({
                    "user": m.user,
                    "is_lead": m.is_sector_lead
                })

    # -------------------------
    # 5️⃣ Response
    # -------------------------
    print(user_sector_list)
    return {
        "tasks": tasks,
        "user": user,
        "user_sector_list": user_sector_list,
        "user_is_lead": user_is_lead,
        "sector_users": sector_users
    }
# ======================================================
#  UPDATE TASK STATUS (STRICT PERMISSIONS)
# ======================================================


@frappe.whitelist()
def update_task_incharge(task_name, user):
    doc = frappe.get_doc("Event Task", task_name)
    doc.incharge = user
    doc.save()
    frappe.db.commit()


@frappe.whitelist()
def update_event_task_status(l2_task_name, status, delay_reason=None):
    task = frappe.get_doc("Event Task", l2_task_name)
    user = frappe.session.user

    # --- PERMISSION LOGIC (unchanged) ---
    if is_admin():
        pass  # Admin bypass
    else:
        sector = get_user_sector()

        # user must belong to same sector
        if task.sector != sector:
            frappe.throw("You cannot update tasks outside your sector")

        # sector lead can update all tasks in sector
        if is_sector_lead():
            pass

        # members: only if assigned
        elif task.incharge != user:
            frappe.throw("You can only update tasks assigned to you")

    # --- STATUS UPDATE ---
    task.status = status

    # --- DELAY LOGIC (NEW) ---
    if status == "Delayed":
        if not delay_reason:
            frappe.throw(
                "Delay reason is required when marking task as Delayed")

        task.delay_reason = delay_reason

    else:
        # Optional: clear previous delay reason if status changes
        task.delay_reason = None

    # Save task & update stats
    task.save()
    update_event_task_stats(task.event)

    frappe.db.commit()


# ======================================================
#  ADD TASK FROM POPUP MODAL
# ======================================================

@frappe.whitelist()
def create_event_task_from_popup(event, l2_task_name, sector, incharge=None, due_date=None, task_description=None):
    task = frappe.new_doc("Event Task")
    task.event = event
    task.l2_task_name = l2_task_name
    task.sector = sector
    task.incharge = incharge
    task.due_date = due_date
    task.task_description = task_description
    task.status = "Pending"
    task.weightage = 0
    task.insert(ignore_permissions=True)
    update_event_task_stats(event)
    return task.name


# ======================================================
#  EVENT READINESS DASHBOARD DATA
# ======================================================

@frappe.whitelist()
def get_event_dashboard_stats():
    """Used by dashboard to show full event overview"""
    return frappe.get_all(
        "Event Readiness",
        fields=["name", "event_name", "event_readiness", "total_tasks",
                "completed_tasks", "pending_tasks", "custom_in_progress_tasks", "delayed_tasks"],
        order_by="creation asc"
    )

# psn_custom_rdb_app/psn_readiness_dashboard/event_logic.py


@frappe.whitelist()
def create_sector_user(full_name, email, sectors):
    # sectors comes as JSON string from JS Dialog — convert safely
    if isinstance(sectors, str):
        sectors = json.loads(sectors or "[]")

    if not sectors:
        frappe.throw("Please add at least one sector assignment")

    # 1) Check if user already exists
    if frappe.db.exists("User", {"email": email}):
        frappe.throw(f"User with email {email} already exists")

    # 2) Create User
    user = frappe.new_doc("User")
    user.first_name = full_name
    user.email = email
    user.user_type = "System User"
    user.send_welcome_email = 0
    user.username = email.split("@")[0]

    # Add required user role
    user.append("roles", {"role": "Event Readiness Role"})

    # If User Doctype still has mandatory "sector", set from first row
    first_sector = sectors[0].get("sector")
    if frappe.db.has_column("User", "sector") and first_sector:
        user.sector = first_sector

    user.insert(ignore_permissions=True)

    # 3) Assign user to each sector + ensure KPI creation
    for row in sectors:
        sector_name = row.get("sector")
        is_lead = cint(row.get("is_sector_lead"))

        if not sector_name:
            continue

        sec_doc = frappe.get_doc("Sector", sector_name)

        # Check if already exists in members
        existing_member = next(
            (m for m in sec_doc.members if m.user == user.name),
            None
        )

        if existing_member:
            existing_member.is_sector_lead = is_lead
        else:
            sec_doc.append("members", {
                "user": user.name,
                "is_sector_lead": is_lead
            })

        sec_doc.save(ignore_permissions=True)

        # Ensure KPI exists
        if not frappe.db.exists("User Sector KPI", {
            "user": user.name,
            "sector": sector_name
        }):
            frappe.get_doc({
                "doctype": "User Sector KPI",
                "user": user.name,
                "sector": sector_name,
                "total_tasks": 0,
                "completed_tasks": 0,
                "pending_tasks": 0,
                "delayed_tasks": 0,
                "avg_completion_time": 0,
            }).insert(ignore_permissions=True)

    frappe.db.commit()
    return user.name


@frappe.whitelist()
def get_task_activity(task_name):
    """Fetch activity for an Event Task (comments / updates / discussions)"""
    return frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "Event Task",
            "reference_name": task_name
        },
        fields=[
            "communication_type", "sender", "subject",
            "content", "creation", "modified_by"
        ],
        order_by="creation desc"
    )


@frappe.whitelist()
def sync_user_kpi():
    sectors = frappe.get_all("Sector", fields=["name"])

    for sec in sectors:
        sec_doc = frappe.get_doc("Sector", sec.name)

        for member in sec_doc.members:
            exists = frappe.db.exists(
                "User Sector KPI",
                {"user": member.user, "sector": sec.name}
            )

            if not exists:
                kpi = frappe.new_doc("User Sector KPI")
                kpi.user = member.user
                kpi.sector = sec.name
                kpi.custom_is_sector_lead = member.is_sector_lead
                kpi.insert(ignore_permissions=True)

    frappe.db.commit()
    return "OK"
