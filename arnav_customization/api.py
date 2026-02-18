import frappe


@frappe.whitelist(allow_guest=True)
def create_sku_via_api(product=None, sku=None):

    frappe.set_user("Administrator")

    doc = frappe.new_doc("SKU")

    doc.append("sku_details", {
        "product": product,
        "sku": sku
    })

    doc.insert(ignore_permissions=True)

    doc.flags.ignore_permissions = True
    doc.submit()

    return {"status": "success"}


