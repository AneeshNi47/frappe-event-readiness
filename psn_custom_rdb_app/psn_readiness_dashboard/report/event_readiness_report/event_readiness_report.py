import frappe


def execute(filters=None):
    data = frappe.db.sql("""
        SELECT
            name as event_name,
            event_readiness,
            start_date,
            end_date
        FROM `tabEvent Readiness`
        WHERE docstatus < 2
        ORDER BY start_date DESC
    """, as_dict=True)

    columns = [
        {"label": "Event", "fieldname": "event_name", "fieldtype": "Link",
            "options": "Event Readiness", "width": 200},
        {"label": "Readiness (%)", "fieldname": "event_readiness",
         "fieldtype": "Percent", "width": 130},
        {"label": "Start Date", "fieldname": "start_date",
            "fieldtype": "Date", "width": 130},
        {"label": "End Date", "fieldname": "end_date",
            "fieldtype": "Date", "width": 130},
    ]

    return columns, data
