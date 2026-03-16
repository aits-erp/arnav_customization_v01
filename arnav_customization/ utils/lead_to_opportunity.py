import frappe
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):

    def set_missing_values(source, target):

        target.opportunity_from = "Lead"
        target.party_name = source.name
        target.customer_name = source.lead_name

        # AUTO COPY CUSTOM FIELDS
        for field in source.meta.fields:
            if field.fieldname.startswith("custom_"):
                if target.meta.has_field(field.fieldname):
                    target.set(field.fieldname, source.get(field.fieldname))

    doc = get_mapped_doc(
        "Lead",
        source_name,
        {
            "Lead": {
                "doctype": "Opportunity",
                "field_map": {
                    "lead_name": "customer_name",
                    "email_id": "contact_email",
                    "mobile_no": "contact_mobile"
                }
            }
        },
        target_doc,
        set_missing_values
    )

    return doc
