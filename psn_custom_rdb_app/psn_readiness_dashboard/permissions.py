import frappe

frappe.flags.ignore_csrf = True


@frappe.whitelist()
def filter_tasks(query_filters=None):
    user = frappe.session.user
    roles = frappe.get_roles(user)

    base_filter = query_filters.copy() if query_filters else {}

    # ------------------------------------------------
    # 1️⃣ Admin → no restriction
    # ------------------------------------------------
    if user == "Administrator" or "Event Readiness Admin" in roles:
        return base_filter

    # ------------------------------------------------
    # 2️⃣ Load user sector mappings
    # ------------------------------------------------
    kpi_entries = frappe.get_all(
        "User Sector KPI",
        filters={"user": user},
        fields=["sector", "custom_is_sector_lead"]
    )

    if not kpi_entries:
        # user has no access to any task
        base_filter["name"] = "__invalid__"
        return base_filter

    user_sectors = [k.sector for k in kpi_entries]
    is_sector_lead = any(k.custom_is_sector_lead for k in kpi_entries)

    # ------------------------------------------------
    # 3️⃣ Sector Lead → sector-based filter
    # ------------------------------------------------
    if is_sector_lead:
        base_filter["sector"] = ["in", user_sectors]
        return base_filter

    # ------------------------------------------------
    # 4️⃣ Sector Member → own tasks only
    # ------------------------------------------------
    base_filter["incharge"] = user
    base_filter["sector"] = ["in", user_sectors]

    return base_filter
