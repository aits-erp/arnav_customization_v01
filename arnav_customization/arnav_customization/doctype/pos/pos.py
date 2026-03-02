import frappe
from frappe.model.document import Document
from frappe.utils import cint

class POS(Document):

	def before_submit(self):
		# 1️⃣ Balance validation
		if abs(self.balance_amount) > 0.01:
			frappe.throw("Cannot submit POS because Balance Amount must be 0.00")

		# 2️⃣ Cash limit validation
		CASH_LIMIT = 195000
		total_cash = 0

		for row in self.payment_details:
			if row.payment_type == "Cash":
				# Individual row validation
				if row.amount > CASH_LIMIT:
					frappe.throw(
						f"Cash amount in a single entry cannot exceed ₹{CASH_LIMIT}. "
						f"Row amount: ₹{row.amount}"
					)

				total_cash += row.amount

		# Total cash validation (if split into multiple rows)
		if total_cash > CASH_LIMIT:
			frappe.throw(
				f"Total Cash payment cannot exceed ₹{CASH_LIMIT}. "
				f"Total Cash entered: ₹{total_cash}"
			)



@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def customer_search_by_mobile(doctype, txt, searchfield, start, page_len, filters):

    return frappe.db.sql("""
        SELECT
            name,
            customer_name,
            mobile_no
        FROM `tabCustomer`
        WHERE
            docstatus < 2
            AND (
                name LIKE %(txt)s
                OR customer_name LIKE %(txt)s
                OR mobile_no LIKE %(txt)s
            )
        ORDER BY name
        LIMIT %(start)s, %(page_len)s
    """, {
        "txt": f"%{txt}%",
        "start": cint(start),
        "page_len": cint(page_len)
    })


# import frappe
# from frappe.model.document import Document


# class POS(Document):
# 	def before_submit(self):
# 		if abs(self.balance_amount) > 0.01:
# 			frappe.throw("Cannot submit POS because Balance Amount must be 0.00")
