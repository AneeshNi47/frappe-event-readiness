# Copyright (c) 2025, PSN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EventTask(Document):
    pass


def get_permission_query_conditions(user):
    if user == "Administrator":
        return ""

    sector, is_lead = frappe.db.get_value(
        "User", user, ["sector", "is_sector_lead"])

    if is_lead:
        return f"""(`tabEvent Task`.sector = "{sector}")"""

    return f"""(`tabEvent Task`.incharge = "{user}")"""


def has_permission(doc, user=None):
    return True
