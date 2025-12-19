# Copyright (c) 2025, PSN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document

frappe.flags.ignore_csrf = True


class EventTask(Document):
    pass


def get_permission_query_conditions(user, doctype=None):
    # --- 1️⃣ Super access ---
    if user == "Administrator":
        return None

    roles = frappe.get_roles(user)

    if "Event Readiness Admin" in roles:
        return None

    # --- 2️⃣ Only apply to Event Task ---
    if doctype != "Event Task":
        return None

    # --- 3️⃣ Fetch ALL sectors for user ---
    kpis = frappe.get_all(
        "User Sector KPI",
        filters={"user": user},
        fields=["sector", "custom_is_sector_lead"]
    )

    if not kpis:
        return "1=0"

    sectors = [k.sector for k in kpis]
    is_lead = any(k.custom_is_sector_lead for k in kpis)

    # --- 4️⃣ Sector Lead ---
    if is_lead:
        sectors_sql = ", ".join(frappe.db.escape(s) for s in sectors)
        return f"`tabEvent Task`.`sector` IN ({sectors_sql})"

    # --- 5️⃣ Sector Member ---
    return f"`tabEvent Task`.`incharge` = {frappe.db.escape(user)}"


def has_permission(doc, user=None):
    return True
