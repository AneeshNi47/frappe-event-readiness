import frappe


def get_user_sector(user):
    return frappe.db.get_value("User", user, "sector")


@frappe.whitelist()
def filter_tasks(query_filters=None):
    user = frappe.session.user
    if user == "Administrator":
        return query_filters or {}

    sector = get_user_sector(user)
    is_lead = frappe.db.exists("Event Sector", {"sector_lead": user})

    base_filter = query_filters or {}

    if is_lead:
        base_filter["sector"] = sector
    else:
        base_filter["in_charge"] = user
        base_filter["sector"] = sector

    return base_filter
