import frappe
from frappe.model.document import Document


class TaskTemplate(Document):

    def validate(self):
        self.ensure_sector_exists()

    def ensure_sector_exists(self):
        if not self.sector:
            return

        # 1️⃣ Direct name match
        if frappe.db.exists("Sector", self.sector):
            return

        # 2️⃣ Match by sector_name (label)
        sector_name = frappe.db.get_value(
            "Sector",
            {"sector_name": self.sector},
            "name"
        )

        if sector_name:
            self.sector = sector_name
            return

        # 3️⃣ Auto-create Sector
        sector = frappe.get_doc({
            "doctype": "Sector",
            "sector_name": self.sector
        })
        sector.insert(ignore_permissions=True)

        # 4️⃣ IMPORTANT: assign actual name
        self.sector = sector.name
