
import frappe
from frappe import _
from frappe.utils import flt


def get_company():
    return frappe.defaults.get_user_default("Company")


def get_available_advance_amount(
    payment_entry, customer, company=None, exclude_invoice=None
):
    """Return available advance after reserving amounts in draft invoices."""

    pe = frappe.db.get_value(
        "Payment Entry",
        payment_entry,
        [
            "name",
            "docstatus",
            "payment_type",
            "party_type",
            "party",
            "company",
            "unallocated_amount",
        ],
        as_dict=True,
    )

    if not pe:
        frappe.throw(_("Payment Entry {0} does not exist.").format(payment_entry))

    if (
        pe.docstatus != 1
        or pe.payment_type != "Receive"
        or pe.party_type != "Customer"
    ):
        frappe.throw(_("Select a submitted customer Receive Payment Entry."))

    if pe.party != customer:
        frappe.throw(_("This Payment Entry belongs to another customer."))

    if company and pe.company != company:
        frappe.throw(_("This Payment Entry belongs to another company."))

    reserved = frappe.db.sql(
        """
        SELECT COALESCE(SUM(adv.allocated_amount), 0)
        FROM `tabSales Invoice Advance` adv
        INNER JOIN `tabSales Invoice` si ON si.name = adv.parent
        WHERE adv.parentfield = 'advances'
          AND adv.reference_type = 'Payment Entry'
          AND adv.reference_name = %s
          AND si.docstatus = 0
          AND (%s IS NULL OR si.name != %s)
        """,
        (payment_entry, exclude_invoice, exclude_invoice),
    )[0][0]

    return max(flt(pe.unallocated_amount) - flt(reserved), 0)

# @frappe.whitelist()
# def fetch_advance_amount(payment_entry, customer):
#     if not frappe.has_permission("Payment Entry", "read"):
#         frappe.throw(_("You do not have permission to read Payment Entries."))

#     amount = get_available_advance_amount(
#         payment_entry=payment_entry,
#         customer=customer,
#         company=get_company(),
#     )

#     payment_rows = frappe.get_all(
#         "POS Payment Details",
#         filters={
#             "parent": payment_entry,
#             "parenttype": "Payment Entry",
#             "parentfield": "custom_payment_details_table",
#         },
#         fields=["amount"],
#     )

#     payment_amount = sum(flt(row.amount) for row in payment_rows)

#     return {
#         "payment_entry": payment_entry,
#         "payment_amount": payment_amount,
#         "available_amount": amount,
#     }


@frappe.whitelist()
def fetch_advance_amount(payment_entry, customer):
    if not frappe.has_permission("Payment Entry", "read"):
        frappe.throw(_("You do not have permission to read Payment Entries."))

    pe = frappe.db.get_value(
        "Payment Entry",
        payment_entry,
        ["name", "party", "party_type"],
        as_dict=True,
    )

    if not pe:
        frappe.throw(_("Payment Entry does not exist."))

    if pe.party_type != "Customer" or pe.party != customer:
        frappe.throw(
            _("This Payment Entry does not belong to the selected customer.")
        )

    payment_rows = frappe.get_all(
        "POS Payment Details",
        filters={
            "parent": payment_entry,
            "parenttype": "Payment Entry",
            "parentfield": "custom_payment_details_table",
        },
        fields=["amount"],
    )

    payment_amount = sum(flt(row.amount) for row in payment_rows)

    return {
        "payment_entry": payment_entry,
        "payment_amount": payment_amount,
    }


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_eligible_payment_entries(
    doctype, txt, searchfield, start, page_len, filters
):
    filters = frappe._dict(filters or {})
    customer = filters.get("customer")
    company = filters.get("company") or get_company()

    if not customer or not company:
        return []

    if not frappe.has_permission("Payment Entry", "read"):
        return []

    return frappe.db.sql(
        """
        SELECT
            pe.name,
            CONCAT(
                pe.name, ' | Available: ',
                FORMAT(
                    GREATEST(
                        pe.unallocated_amount - COALESCE(r.reserved_amount, 0),
                        0
                    ), 2
                )
            )
        FROM `tabPayment Entry` pe
        LEFT JOIN (
            SELECT
                adv.reference_name,
                SUM(adv.allocated_amount) AS reserved_amount
            FROM `tabSales Invoice Advance` adv
            INNER JOIN `tabSales Invoice` si ON si.name = adv.parent
            WHERE adv.parentfield = 'advances'
              AND adv.reference_type = 'Payment Entry'
              AND si.docstatus = 0
            GROUP BY adv.reference_name
        ) r ON r.reference_name = pe.name
        WHERE pe.docstatus = 1
          AND pe.payment_type = 'Receive'
          AND pe.party_type = 'Customer'
          AND pe.party = %(customer)s
          AND pe.company = %(company)s
          AND pe.unallocated_amount - COALESCE(r.reserved_amount, 0) > 0
          AND pe.name LIKE %(txt)s
        ORDER BY pe.posting_date DESC, pe.name DESC
        LIMIT %(start)s, %(page_len)s
        """,
        {
            "customer": customer,
            "company": company,
            "txt": "%" + (txt or "") + "%",
            "start": start,
            "page_len": page_len,
        },
    )


def validate_pos_advance_payments(doc, method=None):
    """Validate Payment Entries selected in POS rows."""

    selected = set()
    company = get_company()

    for row in doc.get("payment_details") or []:
        payment_entry = row.get("custom_payment_entry")
        if not payment_entry:
            continue

        if not doc.client_name:
            frappe.throw(_("Select a customer before selecting a Payment Entry."))

        if payment_entry in selected:
            frappe.throw(
                _("Payment Entry {0} is selected more than once.").format(
                    payment_entry
                )
            )
        selected.add(payment_entry)

        # Lock the Payment Entry row during this transaction.
        frappe.db.sql(
            "SELECT name FROM `tabPayment Entry` WHERE name = %s FOR UPDATE",
            payment_entry,
        )

        available = get_available_advance_amount(
            payment_entry=payment_entry,
            customer=doc.client_name,
            company=company,
        )

        amount = flt(row.amount)
        if amount <= 0 or amount > available + 0.000001:
            frappe.throw(
                _(
                    "Amount for Payment Entry {0} must be greater than zero "
                    "and cannot exceed its available advance {1}."
                ).format(payment_entry, available)
            )


def validate_sales_invoice_advances(doc, method=None):
    """Prevent duplicate or excessive Payment Entry advance allocations."""

    if doc.is_return:
        return

    selected = set()

    for row in doc.get("advances") or []:
        if row.reference_type != "Payment Entry":
            continue

        payment_entry = row.reference_name
        if not payment_entry:
            frappe.throw(_("Select a Payment Entry in the Advances table."))

        if payment_entry in selected:
            frappe.throw(
                _("Payment Entry {0} appears more than once in Advances.").format(
                    payment_entry
                )
            )
        selected.add(payment_entry)

        frappe.db.sql(
            "SELECT name FROM `tabPayment Entry` WHERE name = %s FOR UPDATE",
            payment_entry,
        )

        available = get_available_advance_amount(
            payment_entry=payment_entry,
            customer=doc.customer,
            company=doc.company,
            exclude_invoice=doc.name,
        )

        allocated = flt(row.allocated_amount)

        if allocated <= 0:
            frappe.throw(_("Advance allocation must be greater than zero."))

        if allocated > available + 0.000001:
            frappe.throw(
                _(
                    "Payment Entry {0} has only {1} available, but {2} is allocated."
                ).format(payment_entry, available, allocated)
            )
