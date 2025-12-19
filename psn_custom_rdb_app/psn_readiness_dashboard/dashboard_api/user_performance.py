import frappe


@frappe.whitelist()
def get_user_performance():
    current_user = frappe.session.user

    is_admin = frappe.has_role("Event Readiness Admin", current_user)

    # sectors where current user is a member or lead
    my_kpis = frappe.get_all(
        "User Sector KPI",
        filters={"user": current_user},
        fields=["sector", "custom_is_sector_lead"]
    )

    my_sectors = {k.sector for k in my_kpis}
    is_sector_lead = any(k.custom_is_sector_lead for k in my_kpis)

    # -------------------------------------------------
    # 1️⃣ Build aggregated leaderboard (as confirmed)
    # -------------------------------------------------
    rows = frappe.get_all(
        "User Sector KPI",
        fields=[
            "user",
            "sector",
            "kpi_score",
            "avg_response_hrs",
            "on_time_percentage",
            "completed_tasks",
            "pending_tasks",
            "in_progress_tasks",
            "delayed_tasks",
            "total_tasks",
            "custom_is_sector_lead"
        ]
    )

    from collections import defaultdict
    users = defaultdict(lambda: {
        "name": "",
        "tasks_completed": 0,
        "tasks_assigned": 0,
        "pending": 0,
        "in_progress": 0,
        "delayed": 0,
        "kpi_scores": [],
        "response_times": [],
        "on_time_weighted_sum": 0,
        "on_time_weight": 0,
        "is_lead": False,
        "sectors": set()
    })

    for r in rows:
        u = users[r.user]
        u["name"] = frappe.db.get_value("User", r.user, "full_name") or r.user
        u["sectors"].add(r.sector)

        u["tasks_completed"] += r.completed_tasks or 0
        u["tasks_assigned"] += r.total_tasks or 0
        u["pending"] += r.pending_tasks or 0
        u["in_progress"] += r.in_progress_tasks or 0
        u["delayed"] += r.delayed_tasks or 0

        if r.kpi_score is not None:
            u["kpi_scores"].append(r.kpi_score)

        if r.avg_response_hrs and r.avg_response_hrs > 0:
            u["response_times"].append(r.avg_response_hrs)

        if r.on_time_percentage is not None and r.completed_tasks:
            u["on_time_weighted_sum"] += r.on_time_percentage * r.completed_tasks
            u["on_time_weight"] += r.completed_tasks

        if r.custom_is_sector_lead:
            u["is_lead"] = True

    # -------------------------------------------------
    # 2️⃣ Build final list
    # -------------------------------------------------
    leaderboard = []

    for user, u in users.items():
        record = {
            "user": user,
            "name": u["name"],
            "role": "Sector Lead" if u["is_lead"] else "Sector Member",
            "tasksCompleted": u["tasks_completed"],
            "tasksAssigned": u["tasks_assigned"],
            "avgResponseTime": round(
                sum(u["response_times"]) / len(u["response_times"]), 2
            ) if u["response_times"] else 0,
            "onTimeCompletion": round(
                u["on_time_weighted_sum"] / u["on_time_weight"], 2
            ) if u["on_time_weight"] else 0,
            "performance": round(
                sum(u["kpi_scores"]) / len(u["kpi_scores"]), 2
            ) if u["kpi_scores"] else 0,
            "sectors": list(u["sectors"])
        }

        leaderboard.append(record)

    # -------------------------------------------------
    # 3️⃣ APPLY VISIBILITY RULES
    # -------------------------------------------------
    if is_admin:
        return leaderboard

    if is_sector_lead:
        return [
            u for u in leaderboard
            if set(u["sectors"]) & my_sectors
        ]

    # sector member → only self
    return [
        u for u in leaderboard
        if u["user"] == current_user
    ]
