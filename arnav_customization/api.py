import frappe

@frappe.whitelist(allow_guest=True)
def create_sku_via_api(product=None, sku=None):

    if not product or not sku:
        return {"status": "error", "msg": "Missing product or sku"}

    doc = frappe.new_doc("SKU")

    doc.append("sku_details", {
        "product": product,
        "sku": sku
    })

    doc.insert(ignore_permissions=True)
    doc.submit()

    return {"status": "success", "name": doc.name}

