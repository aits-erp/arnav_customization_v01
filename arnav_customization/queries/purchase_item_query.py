import frappe
from frappe.desk.search import search_link


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def purchase_item_query(doctype, txt, searchfield, start, page_len, filters):

    conditions = []

    # Ensure only purchase items appear
    conditions.append("custom_sub_group_1 = 'Purchase'")

    # Standard search condition
    if txt:
        conditions.append(f"({searchfield} like %(txt)s or item_name like %(txt)s)")

    condition_sql = " AND ".join(conditions)

    return frappe.db.sql(
        f"""
        SELECT
            name,
            item_name,
            item_group,
            stock_uom
        FROM
            `tabItem`
        WHERE
            disabled = 0
            AND {condition_sql}
        ORDER BY
            name
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "txt": f"%{txt}%",
            "start": start,
            "page_len": page_len
        },
    )