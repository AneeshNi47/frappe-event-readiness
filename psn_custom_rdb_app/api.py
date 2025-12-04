import frappe


@frappe.whitelist()
def whoami():
    """Return the currently logged-in user"""
    return frappe.session.user
