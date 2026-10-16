from frappe import _


def get_data():
	"""Show the Sales Returns that reference this POS through custom_pos."""
	return {
		"fieldname": "custom_pos",
		"non_standard_fieldnames": {"Sales Invoice": "custom_pos"},
		"transactions": [
			{
				"label": _("Sales Returns"),
				"items": ["Sales Invoice"],
			}
		],
	}
