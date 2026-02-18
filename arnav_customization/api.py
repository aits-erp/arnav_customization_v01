import frappe

@frappe.whitelist()
def create_sku_via_api(product, sku):

    doc = frappe.new_doc("SKU")

    doc.append("sku_details", {
        "product": product,
        "sku": sku
    })

    doc.insert(ignore_permissions=True)
    doc.submit()

    return {"status": "success", "name": doc.name}
