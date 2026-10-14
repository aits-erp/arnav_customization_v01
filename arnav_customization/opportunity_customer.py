"""Link Customers created from an Opportunity back to that Opportunity."""

import frappe


def link_new_customer_to_opportunity(customer, method=None):
	"""Set Opportunity.custom_customer after its Customer has been saved.

	ERPNext's standard Opportunity-to-Customer action stores the source in
	``opportunity_name``. The custom source field is retained for the custom
	Opportunity button and older routes.
	"""
	opportunity_name = customer.get("opportunity_name") or customer.get(
		"custom_source_opportunity"
	)
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


def backfill_customer_opportunity_links():
	"""Link existing Customers that were created from standard Opportunities.

	The job only fills blank Opportunity links. It never replaces a Customer
	selected manually by a user.
	"""
	if not frappe.db.table_exists("Customer"):
		return

	customers = frappe.get_all(
		"Customer",
		filters={"opportunity_name": ["is", "set"]},
		fields=["name", "opportunity_name"],
	)
	for customer in customers:
		if not frappe.db.exists("Opportunity", customer.opportunity_name):
			continue

		linked_customer = frappe.db.get_value(
			"Opportunity", customer.opportunity_name, "custom_customer"
		)
		if not linked_customer:
			frappe.db.set_value(
				"Opportunity",
				customer.opportunity_name,
				"custom_customer",
				customer.name,
				update_modified=False,
			)
