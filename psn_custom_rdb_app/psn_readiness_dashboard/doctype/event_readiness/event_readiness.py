# Copyright (c) 2025, PSN and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class EventReadiness(Document):
    pass


def get_permission_query_conditions(user, doctype=None):
    if user == "Administrator":
        return None

    roles = frappe.get_roles(user)

    if "Event Readiness Admin" in roles:
        return None

    # Sector Lead → all events
    if "Sector Lead" in roles:
        return None

    # Sector Member → only events where user has tasks
    return f"""
        `tabEvent Readiness`.`name` IN (
            SELECT DISTINCT event
            FROM `tabEvent Task`
            WHERE incharge = {frappe.db.escape(user)}
        )
    """
