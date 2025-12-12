# Copyright (c) 2025, PSN and contributors
# For license information, please see license.txt

from frappe.utils.background_jobs import enqueue
import frappe
from frappe.model.document import Document


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


def calculate_score_for_user_sector(user, sector):
    completed = frappe.db.count(
        "Event Task", {"sector": sector,
                       "incharge": user, "status": "Completed"}
    )
    delayed = frappe.db.count(
        "Event Task", {"sector": sector, "incharge": user, "status": "Delayed"}
    )
    total = frappe.db.count(
        "Event Task", {"sector": sector, "incharge": user}
    )
    # Example formula
    score = 0
    if total > 0:
        score = (completed * 1) - (delayed * 2)
    return score


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
    """
    Background job that recalculates KPIs for all records.
    """
    kpi_rows = frappe.get_all("User Sector KPI", fields=[
                              "name", "user", "sector"])
    for row in kpi_rows:
        score = calculate_score_for_user_sector(row.user, row.sector)
        # Update KPI record
        frappe.db.set_value("User Sector KPI", row.name, "kpi_score", score)
    frappe.db.commit()
