# Copyright (c) 2025, PSN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue

frappe.flags.ignore_csrf = True


class UserSectorKPI(Document):
    pass


@frappe.whitelist()
def sync_user_sector_kpi():
    """Ensure every sector member has a corresponding KPI entry."""
    created = 0
    skipped = 0

    sectors = frappe.get_all("Sector", fields=["name"])

    for sec in sectors:
        members = frappe.get_all(
            "Sector Member",
            filters={"parent": sec["name"]},
            fields=["user", "is_sector_lead"]
        )

        for m in members:
            exists = frappe.db.exists(
                "User Sector KPI",
                {"user": m["user"], "sector": sec["name"]}
            )

            if exists:
                skipped += 1
                continue

            doc = frappe.new_doc("User Sector KPI")
            doc.user = m["user"]
            doc.sector = sec["name"]
            doc.custom_is_sector_lead = m["is_sector_lead"]
            doc.insert(ignore_permissions=True)

            created += 1

    frappe.db.commit()

    return {
        "status": "success",
        "created": created,
        "skipped": skipped,
        "message": f"KPI Sync Completed: {created} added, {skipped} already existed"
    }


def get_avg_response_time_hours(user, sector):
    tasks = frappe.get_all(
        "Event Task",
        filters={"sector": sector, "incharge": user},
        fields=["name", "creation"]
    )

    total_hours = 0
    count = 0

    for t in tasks:
        first_update = frappe.get_value(
            "Version",
            {
                "ref_doctype": "Event Task",
                "docname": t.name
            },
            "creation",
            order_by="creation asc"
        )

        if first_update:
            diff = (first_update - t.creation).total_seconds() / 3600
            total_hours += diff
            count += 1

    if count == 0:
        return None

    return round(total_hours / count, 2)


def get_on_time_percentage(user, sector):
    completed_tasks = frappe.get_all(
        "Event Task",
        filters={
            "sector": sector,
            "incharge": user,
            "status": "Completed"
        },
        fields=["name", "due_date", "modified"]
    )

    if not completed_tasks:
        return None

    on_time = 0

    for t in completed_tasks:
        if t.due_date and t.modified.date() <= t.due_date:
            on_time += 1

    return round((on_time / len(completed_tasks)) * 100, 2)


def calculate_time_weighted_kpi(user, sector):
    (
        base_score,
        completed,
        delayed,
        pending,
        in_progress,
        total
    ) = calculate_score_for_user_sector(user, sector)

    avg_response = get_avg_response_time_hours(user, sector)
    on_time_pct = get_on_time_percentage(user, sector)

    # Normalize response time (ideal = 4 hrs)
    if avg_response is None:
        response_score = 50
    else:
        response_score = max(0, min(100, (4 / avg_response) * 100))

    # Normalize on-time %
    delivery_score = on_time_pct if on_time_pct is not None else 50

    # Final weighted KPI
    final_score = round(
        (base_score * 0.5) +
        (delivery_score * 0.3) +
        (response_score * 0.2),
        2
    )

    return {
        "kpi_score": final_score,
        "avg_response_hrs": avg_response,
        "on_time_percentage": on_time_pct,
        "completed": completed,
        "delayed": delayed,
        "pending": pending,
        "in_progress": in_progress,
        "total": total
    }


def calculate_score_for_user_sector(user, sector):
    completed = frappe.db.count(
        "Event Task",
        {"sector": sector, "incharge": user, "status": "Completed"}
    )
    delayed = frappe.db.count(
        "Event Task",
        {"sector": sector, "incharge": user, "status": "Delayed"}
    )
    in_progress = frappe.db.count(
        "Event Task",
        {"sector": sector, "incharge": user, "status": "In Progress"}
    )
    pending = frappe.db.count(
        "Event Task",
        {"sector": sector, "incharge": user, "status": "Pending"}
    )

    total = completed + delayed + in_progress + pending

    if total == 0:
        return 0, completed, delayed, pending, in_progress, total

    # Weighted raw score
    raw_score = (
        (completed * 1.0)
        - (delayed * 1.5)
        - (pending * 0.25)
    )

    # Normalize to 0–100
    score = max(0, round((raw_score / total) * 100, 2))

    return score, completed, delayed, pending, in_progress, total


@frappe.whitelist()
def recalculate_kpi_scores():
    """
    Trigger a background job for recalculation.
    """
    enqueue(
        "psn_custom_rdb_app.psn_readiness_dashboard.doctype.user_sector_kpi.user_sector_kpi.execute_kpi_recalculation",
        queue="long",
        timeout=300
    )
    return "Background job started"


def execute_kpi_recalculation():
    kpi_rows = frappe.get_all(
        "User Sector KPI",
        fields=["name", "user", "sector"]
    )

    for row in kpi_rows:
        result = calculate_time_weighted_kpi(row.user, row.sector)

        if result["avg_response_hrs"] is None:
            print("avg was none")
            avg_response_hrs = 0
        else:
            avg_response_hrs = result["avg_response_hrs"]

        if result["on_time_percentage"] is None:
            print("on time was none")
            on_time_percentage = 0
        else:
            on_time_percentage = result["on_time_percentage"]

        frappe.db.set_value(
            "User Sector KPI",
            row.name,
            {
                "kpi_score": result["kpi_score"],
                "avg_response_hrs": avg_response_hrs,
                "on_time_percentage": on_time_percentage,
                "completed_tasks": result["completed"],
                "delayed_tasks": result["delayed"],
                "pending_tasks": result["pending"],
                "in_progress_tasks": result["in_progress"],
                "total_tasks": result["total"]
            }
        )

    frappe.db.commit()


def recalculate_kpi_for_user_sector(user, sector):
    result = calculate_time_weighted_kpi(user, sector)

    kpi_name = frappe.db.get_value(
        "User Sector KPI",
        {"user": user, "sector": sector},
        "name"
    )

    if not kpi_name:
        return

    if not result.get("avg_response_hrs"):
        print("avg was none")
        avg_response_hrs = 0
    if not result.get("on_time_percentage"):
        print("on time was none")
        on_time_percentage = 0

    frappe.db.set_value(
        "User Sector KPI",
        kpi_name,
        {
            "kpi_score": result["kpi_score"],
            "avg_response_hrs": avg_response_hrs,
            "on_time_percentage": on_time_percentage,
            "completed_tasks": result["completed"],
            "delayed_tasks": result["delayed"],
            "pending_tasks": result["pending"],
            "in_progress_tasks": result["in_progress"],
            "total_tasks": result["total"]
        }
    )
