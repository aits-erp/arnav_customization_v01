app_name = "arnav_customization"
app_title = "arnav_customization"
app_publisher = "aits"
app_description = "many fields and doctypes with custom modifications"
app_email = "nikhil@aitsind.com"
app_license = "mit"

app_include_js = "/assets/arnav_customization/js/design_code_breakup.js"

doctype_js = {
    "Credit Note": "public/js/credit_note.js",
    "Debit Note": "public/js/debit_note.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    "Stock Entry": "public/js/stock_entry.js",
    "Quotation": "public/js/quotation.js",
	"Opportunity": "public/js/opportunity.js",
    "Payment Entry": "public/js/payment_entry.js"
}

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            ["module", "=", "arnav_customization"]
        ]
    }
]

# Runs after fixtures are imported, so the custom_pos_detail column is present
# before the historical Sales Return backfill queries it.
after_migrate = [
    "arnav_customization.patches.backfill_pos_return_detail_references.execute",
    "arnav_customization.opportunity_customer.backfill_customer_opportunity_links"
]

# Frappe's orphan-DocType cleanup can misidentify newly introduced standard
# DocTypes during migrate. Explicit controller registration keeps these source
# backed DocTypes available after the cleanup phase.
override_doctype_class = {
    "ELEMENT_CODE": "arnav_customization.breakup_doctypes.doctype.element_code.element_code.ElementCode",
    "SET_CODE": "arnav_customization.breakup_doctypes.doctype.set_code.set_code.SetCode",
}

# Preserve the standard Sales Invoice dashboard and add the one-to-one source
# POS reference used by Sales Returns.
override_doctype_dashboards = {
    "Sales Invoice": "arnav_customization.sales_invoice_dashboard.get_data",
}



doc_events = {
	  "SKU Master": {
        "on_submit": "arnav_customization.shopify_sync.sync_each_sku_as_product"
    },
	 
    "Sales Order": {
        "after_insert": "arnav_customization.shopify_order_patch.smart_sku_mapper"
    },
    "Customer": {
        "after_insert": "arnav_customization.opportunity_customer.link_new_customer_to_opportunity",
        "on_update": "arnav_customization.opportunity_customer.link_new_customer_to_opportunity"
    },
        "Sales Invoice": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.sales_invoice.process",
        "before_submit": "arnav_customization.arnav_customization.doctype.pos.pos.validate_pos_return_quantities",
        "on_submit": "arnav_customization.arnav_customization.doctype.pos.pos.sync_sku_status_for_pos_return",
        "on_cancel": "arnav_customization.arnav_customization.doctype.pos.pos.sync_sku_status_for_pos_return"
    },

    "Quotation": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.quotation.process"
    },

    "Debit Note": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.debit_note.process"
    },

    "Stock Entry": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.stock_entry.process",
        "before_validate": [
            "arnav_customization.sku_mapping_backend.handlers.stock_entry.process",
            "arnav_customization.sku_mapping_backend.handlers.stock_entry.material_transfer_qty_handler"
        ]
    },
    "Credit Note": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.credit_note.process"
    },
    # "Payment Entry": {
    #     "validate": "arnav_customization.sku_mapping_backend.payment_entry.calculate_custom_paid_amount"
    # }
    
    "Payment Entry": {
        "validate": "arnav_customization.sku_mapping_backend.payment_entry.calculate_custom_paid_amount",
        "before_submit": "arnav_customization.sku_mapping_backend.payment_entry.validate_payment_amount_match"
    }
}

