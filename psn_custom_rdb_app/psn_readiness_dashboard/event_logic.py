import frappe
from frappe.utils import add_days, nowdate

# ======================================================
#  HELPER FUNCTIONS FOR PERMISSIONS
# ======================================================


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
    user_sector = frappe.db.get_value("User", user, "sector")
    is_lead = frappe.db.get_value("User", user, "is_sector_lead") or 0

    tasks = frappe.get_all(
        "Event Task",
        filters={"event": event_name, "sector": user_sector},
        fields=["name", "l2_task_name", "sector",
                "status", "incharge", "creation"],
        order_by="creation ASC"
    )

    return {
        "tasks": tasks,
        "user_sector": user_sector,
        "is_lead": int(is_lead),
        "user": user
    }


# ======================================================
#  UPDATE TASK STATUS (STRICT PERMISSIONS)
# ======================================================

@frappe.whitelist()
def update_event_task_status(l2_task_name, status):
    task = frappe.get_doc("Event Task", l2_task_name)
    user = frappe.session.user

    if is_admin():
        # Admin bypass
        pass

    else:
        sector = get_user_sector()

        # user must belong to same sector
        if task.sector != sector:
            frappe.throw("You cannot update tasks outside your sector")

        # lead can update all tasks in sector
        if is_sector_lead():
            pass

        # members: only if assigned
        elif task.incharge != user:
            frappe.throw("You can only update tasks assigned to you")

    task.status = status
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
