import frappe
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def make_opportunity(source_name, target_doc=None):
	frappe.msgprint("CUSTOM METHOD RUNNING")
    doc = get_mapped_doc(
        "Lead",
        source_name,
        {
            "Lead": {
                "doctype": "Opportunity",
                "field_map": {

                    # STANDARD FIELDS
                    "lead_name": "customer_name",
                    "email_id": "contact_email",
                    "mobile_no": "contact_mobile",

                    # CUSTOM FIELDS
                    "custom_source_type": "custom_source_type",
                    "custom_lead_source": "custom_lead_source",
                    "custom_category_interest": "custom_category_interest",
                    "custom_metal_interest": "custom_metal_interest",
                    "custom_lead_owner_1": "custom_lead_owner_1",
                    "custom_lead_owner_2": "custom_lead_owner_2",
                    "custom_budget_range": "custom_budget_range"
                }
            }
        },
        target_doc,
        set_missing_values
    )

    return doc


def set_missing_values(source, target):

    target.opportunity_from = "Lead"
    target.party_name = source.name
    target.customer_name = source.lead_name
