import csv
import json
import math
import os

import frappe
from frappe.utils import add_days, cint, flt, nowdate

from psn_custom_rdb_app.psn_readiness_dashboard.doctype.user_sector_kpi.user_sector_kpi import \
    recalculate_kpi_for_user_sector

frappe.flags.ignore_csrf = True


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


def is_sector_lead():
    return frappe.db.get_value("User", frappe.session.user, "is_sector_lead") == 1


def enqueue_default_event_tasks(doc, method=None):
    """
    Enqueue background job for default task creation
    Triggered from Frappe UI event creation
    """
    if not doc.use_default_tasks:
        return
    doc.db_set("custom_tasks_generation_status", "In Progress")
    frappe.enqueue(
        "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.create_default_event_tasks_bg",
        queue="long",
        event_id=doc.name,
        timeout=1200,
        enqueue_after_commit=True
    )
    doc.db_set("custom_tasks_generation_status", "Completed")


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


@frappe.whitelist()
def get_tasks_for_event(event_name):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    is_admin = "Event Readiness Admin" in roles or user == "Administrator"
    is_sector_lead = False
    user_sectors = []

    # -------------------------
    # Load sector mappings
    # -------------------------
    kpi_entries = frappe.get_all(
        "User Sector KPI",
        filters={"user": user},
        fields=["sector", "custom_is_sector_lead"]
    )

    if kpi_entries:
        user_sectors = [k.sector for k in kpi_entries]
        is_sector_lead = any(k.custom_is_sector_lead for k in kpi_entries)

    # -------------------------
    # Build task filters
    # -------------------------
    filters = {"event": event_name}

    if not is_admin:
        # Sector Lead → sector-based visibility
        if is_sector_lead and user_sectors:
            filters["sector"] = ["in", user_sectors]

        # Sector Member → only assigned tasks
        else:
            filters["incharge"] = user

    # -------------------------
    # Fetch tasks
    # -------------------------
    tasks = frappe.get_all(
        "Event Task",
        filters=filters,
        fields=[
            "name",
            "l2_task_name",
            "sector",
            "status",
            "incharge",
            "creation",
            "due_date",
            "progress"
        ],
        order_by="creation asc"
    )

    # -------------------------
    # Sector → Users mapping (ONLY for admins & leads)
    # -------------------------
    sector_users = {}

    if is_admin or is_sector_lead:
        relevant_sectors = list({t.sector for t in tasks if t.sector})

        if relevant_sectors:
            members = frappe.get_all(
                "User Sector KPI",
                filters={"sector": ["in", relevant_sectors]},
                fields=["sector", "user", "custom_is_sector_lead"]
            )

            for m in members:
                sector_users.setdefault(m.sector, []).append({
                    "user": m.user,
                    "is_lead": m.custom_is_sector_lead
                })

    return {
        "tasks": tasks,
        "user": user,
        "user_sector_list": user_sectors,
        "user_is_lead": is_sector_lead,
        "sector_users": sector_users
    }


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
    roles = frappe.get_roles(user)
    if user == "Administrator" or "Event Readiness Admin" in roles:
        pass

    else:
        kpi_entries = frappe.get_all(
            "User Sector KPI",
            filters={"user": user},
            fields=["sector", "custom_is_sector_lead"]
        )

        if not kpi_entries:
            frappe.throw("You are not assigned to any sector")

        user_sectors = [k.sector for k in kpi_entries]
        is_sector_lead = any(k.custom_is_sector_lead for k in kpi_entries)
        # Sector mismatch
        if task.sector not in user_sectors:
            frappe.throw("You cannot update tasks outside your sector")

        # Sector member can update ONLY their own tasks
        if not is_sector_lead and task.incharge != user:
            frappe.throw("You can only update tasks assigned to you")
    task.status = status

    if status == "Delayed":
        if not delay_reason:
            frappe.throw("Delay reason is required")
        task.delay_reason = delay_reason
    else:
        task.delay_reason = None

    task.save()
    update_event_task_stats(task.event)

    frappe.db.commit()


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


@frappe.whitelist()
def get_event_dashboard_stats():
    """Used by dashboard to show full event overview"""
    return frappe.get_all(
        "Event Readiness",
        fields=["name", "event_name", "event_readiness", "total_tasks",
                "completed_tasks", "pending_tasks", "custom_in_progress_tasks", "delayed_tasks"],
        order_by="creation asc"
    )


@frappe.whitelist()
def create_sector_user(full_name, email, sectors):
    if isinstance(sectors, str):
        sectors = json.loads(sectors or "[]")
    if not sectors:
        frappe.throw("Please add at least one sector assignment")
    if frappe.db.exists("User", {"email": email}):
        frappe.throw(f"User with email {email} already exists")
    is_sector_lead = any(cint(row.get("is_sector_lead")) for row in sectors)
    role_to_assign = "Sector Lead" if is_sector_lead else "Sector Member"
    user = frappe.new_doc("User")
    user.first_name = full_name
    user.email = email
    user.user_type = "System User"
    user.send_welcome_email = 0
    user.username = email.split("@")[0]
    user.enabled = 1
    user.append("roles", {"role": role_to_assign})
    first_sector = sectors[0].get("sector")
    if frappe.db.has_column("User", "sector") and first_sector:
        user.sector = first_sector
    user.insert(ignore_permissions=True)
    for row in sectors:
        sector_name = row.get("sector")
        is_lead = cint(row.get("is_sector_lead"))
        if not sector_name:
            continue
        sec_doc = frappe.get_doc("Sector", sector_name)
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
    return {
        "message": "User created successfully",
        "user": user.name,
        "role": role_to_assign
    }


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


def create_default_event_tasks_bg(event_id):
    """
    Background job to create default tasks for an event
    """
    if not frappe.db.exists("Event Readiness", event_id):
        frappe.log_error(f"Event {event_id} not found", "BG Task")
        return

    doc = frappe.get_doc("Event Readiness", event_id)
    if not doc.use_default_tasks:
        return

    templates = frappe.get_all(
        "Task Template",
        fields=["sector", "task_name", "description", "duration_days"]
    )

    for tmpl in templates:
        if frappe.db.exists(
            "Event Task",
            {
                "event": doc.name,
                "sector": tmpl.sector,
                "l2_task_name": tmpl.task_name
            }
        ):
            continue

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


@frappe.whitelist()
def import_task_templates(csv_file):
    """
    Custom importer for Task Template (Frappe v15 safe)

    csv_file:
      - file_url from Attach field
      - Example: /private/files/Task Template - Task Template.csv
    """

    # -------------------------------------------------
    # 1️⃣ Validate input
    # -------------------------------------------------
    if not csv_file:
        frappe.throw("CSV file is required")

    # -------------------------------------------------
    # 2️⃣ Resolve absolute file path (v15 SAFE)
    # -------------------------------------------------
    # csv_file already contains /private/files/...
    site_path = frappe.get_site_path()
    relative_path = csv_file.lstrip("/")
    file_path = os.path.join(site_path, relative_path)

    if not os.path.exists(file_path):
        frappe.throw(f"File not found on disk: {file_path}")

    # -------------------------------------------------
    # 3️⃣ Read CSV file
    # -------------------------------------------------
    created = 0
    skipped = 0
    errors = []

    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)

        # -------------------------------------------------
        # 4️⃣ Process rows
        # -------------------------------------------------
        for row_no, row in enumerate(reader, start=2):
            try:
                # ---- CSV fields (AS PER YOUR SYSTEM)
                template_name = (row.get("Template Name") or "").strip()
                sector_label = (row.get("Sector") or "").strip()
                duration_days = row.get("Duration Days")
                task_name = (row.get("L2 Indicators") or "").strip()
                l1_indicator = (row.get("L1 Indicator") or "").strip()
                description = (row.get("Description") or "").strip()

                if not sector_label or not task_name:
                    raise Exception("Missing Sector or L2 Task Name")

                # -------------------------------------------------
                # Ensure Sector exists
                # -------------------------------------------------
                sector = frappe.db.get_value(
                    "Sector",
                    {"sector_name": sector_label},
                    "name"
                )

                if not sector:
                    sector_doc = frappe.get_doc({
                        "doctype": "Sector",
                        "sector_name": sector_label
                    })
                    sector_doc.insert(ignore_permissions=True)
                    sector = sector_doc.name

                # -------------------------------------------------
                # Avoid duplicate Task Templates
                # -------------------------------------------------
                if frappe.db.exists("Task Template", {
                    "template_name": template_name,
                    "sector": sector,
                    "l1_indicator": l1_indicator,
                    "task_name": task_name,
                    "duration_days": int(duration_days or 0)
                }):
                    skipped += 1
                    continue

                # -------------------------------------------------
                # Create Task Template
                # -------------------------------------------------
                task = frappe.get_doc({
                    "doctype": "Task Template",
                    "template_name": template_name,
                    "sector": sector,
                    "l1_indicator": l1_indicator,
                    "task_name": task_name,
                    "description": description,
                    "duration_days": int(duration_days or 0)
                })

                task.insert(ignore_permissions=True)
                created += 1

            except Exception as e:
                errors.append({
                    "row": row_no,
                    "error": str(e),
                    "data": row
                })

    # -------------------------------------------------
    # 5️⃣ Return summary
    # -------------------------------------------------
    return {
        "created": created,
        "skipped": skipped,
        "errors": errors
    }


@frappe.whitelist()
def recalculate_sector_readiness(sector):
    if not sector:
        frappe.throw("Sector is required")

    stats = frappe.db.sql("""
        SELECT
            COUNT(*) AS total_tasks,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks,
            SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress_tasks
        FROM `tabEvent Task`
        WHERE sector = %s
    """, sector, as_dict=True)[0]

    total_tasks = stats.total_tasks or 0
    completed_tasks = stats.completed_tasks or 0
    in_progress_tasks = stats.in_progress_tasks or 0

    sector_readiness = (
        flt((completed_tasks / total_tasks) * 100, 2)
        if total_tasks > 0 else 0
    )

    sector_doc = frappe.get_doc("Sector", sector)

    sector_doc.total_tasks = total_tasks
    sector_doc.completed_tasks = completed_tasks
    sector_doc.in_progress_tasks = in_progress_tasks
    sector_doc.sector_readiness = sector_readiness

    sector_doc.save(ignore_permissions=True)

    return {
        "total_tasks": total_tasks,
        "completed_tasks": completed_tasks,
        "in_progress_tasks": in_progress_tasks,
        "sector_readiness": sector_readiness
    }


@frappe.whitelist()
def get_sector_detail(sector):
    if not sector:
        frappe.throw("Sector is required")

    sector_doc = frappe.get_doc("Sector", sector)
    members = []
    user_ids = []

    for row in sector_doc.sector_members:
        user_ids.append(row.user)

    user_map = {
        u.name: u
        for u in frappe.get_all(
            "User",
            filters={"name": ["in", user_ids]},
            fields=["name", "full_name", "email", "phone"]
        )
    }
    task_stats = frappe.db.sql("""
        SELECT
            assigned_to,
            COUNT(*) AS total_tasks,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks
        FROM `tabEvent Task`
        WHERE sector = %s
        GROUP BY assigned_to
    """, sector, as_dict=True)

    task_map = {
        t.assigned_to: t
        for t in task_stats
    }
    for row in sector_doc.sector_members:
        user = user_map.get(row.user)
        stats = task_map.get(row.user, {})

        total = stats.total_tasks or 0
        completed = stats.completed_tasks or 0

        performance = (
            int(math.floor((completed / total) * 100 + 0.5))
            if total > 0 else 0
        )

        members.append({
            "id": row.user,
            "name": user.full_name if user else row.user,
            "email": user.email if user else "",
            "phone": user.phone if user else "",
            "avatar": (user.full_name[:2].upper() if user else "NA"),
            "sectors": [{
                "sectorId": sector_doc.name,
                "sectorName": sector_doc.name,
                "isLead": row.is_lead
            }],
            "tasksAssigned": total,
            "tasksCompleted": completed,
            "performance": performance
        })
    return {
        "sector": {
            "id": sector_doc.name,
            "name": sector_doc.name,
            "description": sector_doc.description,
            "readiness": int(math.floor((sector_doc.sector_readiness or 0) + 0.5)),
            "totalMembers": len(members),
            "leads": len([m for m in members if m["sectors"][0]["isLead"]]),
            "activeTasks": sector_doc.in_progress_tasks or 0,
            "completedTasks": sector_doc.completed_tasks or 0
        },
        "members": members
    }


@frappe.whitelist()
def add_sector_member(sector, user, is_lead=0):
    if not sector or not user:
        frappe.throw("Sector and User are required")

    sector_doc = frappe.get_doc("Sector", sector)

    # Prevent duplicates
    if any(row.user == user for row in sector_doc.sector_members):
        frappe.throw("User already added to this sector")

    sector_doc.append("sector_members", {
        "user": user,
        "is_lead": is_lead
    })

    sector_doc.save(ignore_permissions=True)

    return {"status": "success"}
