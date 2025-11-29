import frappe
from frappe.utils import add_days, nowdate


def create_default_event_tasks(doc, method=None):
    """Auto create tasks from template when event is created"""

    if not doc.use_default_tasks:
        return

    templates = frappe.get_all(
        "Task Template",
        fields=["name", "sector", "task_name", "description", "duration_days"]
    )

    for tmpl in templates:

        # Avoid duplicates
        if frappe.db.exists("Event Task", {
            "event": doc.name,
            "sector": tmpl.sector,
            "task_name": tmpl.task_name
        }):
            continue

        # Fetch sector lead
        lead = frappe.db.get_value(
            "Sector Member",
            {"is_sector_lead": 1, "parent": tmpl.sector},
            "user"
        )

        # Create task
        task = frappe.new_doc("Event Task")
        task.event = doc.name
        task.sector = tmpl.sector
        task.sector_lead = lead
        task.l2_task_name = tmpl.task_name
        task.task_description = tmpl.description
        task.status = "Pending"
        task.weightage = 0
        task.progress = 0

        # Use event_date instead of start_date
        base_date = doc.event_date or nowdate()
        task.due_date = add_days(base_date, tmpl.duration_days or 0)

        task.insert(ignore_permissions=True)

    # Update counters on Event Readiness
    update_event_task_stats(doc.name)

    frappe.msgprint("Default tasks have been added to this event.")


def update_task_weightage(doc, method=None):
    """Update task progress + recompute event stats"""

    weightage_map = {
        "Pending": 0,
        "Delayed": 0,
        "In Progress": 50,
        "Completed": 100
    }

    doc.weightage = weightage_map.get(doc.status, 0)
    doc.progress = doc.weightage

    update_event_task_stats(doc.event)


def update_event_task_stats(event_name):
    """Recalculate all task counters and readiness score"""

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


@frappe.whitelist()
def get_tasks_for_event(event_name):
    return frappe.get_all(
        "Event Task",
        filters={"event": event_name},
        fields=["name", "l2_task_name", "sector", "status", "creation"],
        order_by="creation ASC"
    )


@frappe.whitelist()
def update_event_task_status(l2_task_name, status):
    task = frappe.get_doc("Event Task", l2_task_name)
    task.status = status
    task.save(ignore_permissions=True)
    frappe.db.commit()
    return "ok"


def after_insert_user(doc, method):
    if doc.sector:
        frappe.get_doc({
            "doctype": "User Permission",
            "user": doc.name,
            "allow": "Sector",
            "for_value": doc.sector
        }).insert(ignore_permissions=True)
