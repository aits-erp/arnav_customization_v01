import frappe
from frappe.model.document import Document


class SKU(Document):

    def before_save(self):
        self.set_d_no()

    def onload(self):
        # ensures value is visible even if old record is opened
        self.set_d_no()

    def set_d_no(self):
        if not self.sku_master or not self.name:
            return

        # Fetch d_no from SKU Details child table
        d_no = frappe.db.get_value(
            "SKU Details",
            {
                "parent": self.sku_master,
                "sku": self.name   # your field is DATA, not link
            },
            "d_no"
        )

        if d_no:
            self.d_no = d_no