"""Link Customers created from an Opportunity back to that Opportunity."""

import frappe


def link_new_customer_to_opportunity(customer, method=None):
	"""Set Opportunity.custom_customer after its Customer has been saved.

	Only Customers created through the Opportunity action have
	``custom_source_opportunity`` set, so normal Customer creation is unchanged.
	"""
	opportunity_name = customer.get("custom_source_opportunity")
	if not opportunity_name:
		return

	if not frappe.db.exists("Opportunity", opportunity_name):
		frappe.throw("The source Opportunity for this Customer no longer exists.")

	linked_customer = frappe.db.get_value(
		"Opportunity", opportunity_name, "custom_customer"
	)
	if linked_customer and linked_customer != customer.name:
		frappe.throw(
			"Opportunity {0} is already linked to Customer {1}.".format(
				opportunity_name, linked_customer
			)
		)

	frappe.db.set_value(
		"Opportunity", opportunity_name, "custom_customer", customer.name,
		update_modified=False,
	)
