import frappe


@frappe.whitelist()
def whoami():
    """Return the currently logged-in user"""
    return frappe.session.user


# psn_custom_rdb_app/api.py


@frappe.whitelist()
def get_frontend_session_context():
    """Return the current user and whether they can access the React app."""
    user = frappe.session.user

    if user == "Guest":
        frappe.throw("Not logged in", frappe.AuthenticationError)

    roles = frappe.get_roles(user)

    # example: only allow Event Readiness users or System Manager
    allowed_roles = {"Event Readiness User", "System Manager"}
    has_access = bool(allowed_roles.intersection(set(roles)))

    return {
        "user": user,
        "roles": roles,
        "has_access": has_access,
    }
