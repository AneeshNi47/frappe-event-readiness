import frappe
from frappe.utils import cint


@frappe.whitelist()
def get_all_sectors():
    return frappe.get_all(
        "Sector",
        fields=["name"]
    )


@frappe.whitelist()
def get_users_for_sector(sector):
    return frappe.get_all(
        "User Sector KPI",
        filters={"sector": sector},
        fields=["user"]
    )


@frappe.whitelist()
def get_allowed_sectors(user, roles):
    # Event Readiness Admin → all sectors
    if "Event Readiness Admin" in roles:
        return frappe.get_all(
            "Sector",
            fields=["name", "description", "sector_readiness",
                    "completed_tasks", "in_progress_tasks"]
        )

    # Sector Lead / Member → sectors where user exists in child table
    if "Sector Lead" in roles or "Sector Member" in roles:
        return frappe.get_all(
            "Sector",
            filters={
                "name": ["in", frappe.get_all(
                    "Sector Member",
                    filters={"user": user},
                    pluck="parent"
                )]
            },
            fields=["name", "description", "sector_readiness",
                    "completed_tasks", "in_progress_tasks"]
        )

    return frappe.get_all(
        "Sector",
        fields=["name", "description", "sector_readiness",
                "completed_tasks", "in_progress_tasks"]
    )


@frappe.whitelist()
def get_sectors_dashboard():
    user = frappe.session.user
    roles = frappe.get_roles(user)

    sectors = get_allowed_sectors(user, roles)
    sector_names = [s.name for s in sectors]

    if not sector_names:
        return {
            "sectors": [],
            "summary": {}
        }

    # ----------------------------
    # Members (child table)
    # ----------------------------
    members_data = frappe.db.sql("""
        SELECT
            parent AS sector,
            COUNT(*) AS total_members
        FROM `tabSector Member`
        WHERE parent IN %(sectors)s
        GROUP BY parent
    """, {"sectors": sector_names}, as_dict=True)

    members_map = {
        m.sector: cint(m.total_members)
        for m in members_data
    }

    # ----------------------------
    # Tasks data
    # ----------------------------
    tasks_data = frappe.db.sql("""
        SELECT
            sector,
            SUM(CASE WHEN status IN ('Pending', 'In Progress') THEN 1 ELSE 0 END) AS active_tasks,
            SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) AS completed_tasks
        FROM `tabEvent Task`
        WHERE sector IN %(sectors)s
        GROUP BY sector
    """, {"sectors": sector_names}, as_dict=True)

    tasks_map = {
        t.sector: {
            "active": cint(t.active_tasks),
            "completed": cint(t.completed_tasks)
        }
        for t in tasks_data
    }

    # ----------------------------
    # Build sector list
    # ----------------------------
    sector_list = []
    total_members = 0
    total_active_tasks = 0
    total_completed_tasks = 0
    total_readiness = 0

    for sector in sectors:
        members = members_map.get(sector.name, 0)
        tasks = tasks_map.get(sector.name, {})

        active_tasks = tasks.get("active", 0)
        completed_tasks = tasks.get("completed", 0)

        sector_list.append({
            "id": sector.name,
            "name": sector.name,
            "sector_readiness": int(round(sector.sector_readiness or 0)),
            "totalMembers": members,
            "activeTasks": active_tasks,
            "completedTasks": completed_tasks
        })

        total_members += members
        total_active_tasks += active_tasks
        total_completed_tasks += completed_tasks
        total_readiness += 10

    # ----------------------------
    # Summary block
    # ----------------------------
    summary = {
        "totalSectors": len(sector_list),
        "totalMembers": total_members,
        "totalActiveTasks": total_active_tasks,
        "totalCompletedTasks": total_completed_tasks,
        "averageReadiness": round(total_readiness / len(sector_list)) if sector_list else 0
    }

    return {
        "sectors": sector_list,
        "summary": summary
    }


@frappe.whitelist()
def create_sector(name, description):
    if frappe.db.exists("Sector", name):
        frappe.throw("Sector already exists")

    sector = frappe.get_doc({
        "doctype": "Sector",
        "sector_name": name,   # if you have a separate field
        "description": description
    })

    sector.insert(ignore_permissions=True)

    return {
        "name": sector.name
    }
