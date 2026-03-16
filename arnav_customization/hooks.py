app_name = "arnav_customization"
app_title = "arnav_customization"
app_publisher = "aits"
app_description = "many fields and doctypes with custom modifications"
app_email = "nikhil@aitsind.com"
app_license = "mit"

doctype_js = {
    "Credit Note": "public/js/credit_note.js",
    "Debit Note": "public/js/debit_note.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    "Stock Entry": "public/js/stock_entry.js",
    "Quotation": "public/js/quotation.js",
	"Opportunity": "public/js/opportunity.js"
}

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            # ["dt", "in", [
            #     "Sales Invoice Item"
            # ]],
            ["module", "=", "arnav_customization"]
        ]
    }
]



doc_events = {
	  "SKU Master": {
        "on_submit": "arnav_customization.shopify_sync.sync_to_shopify"
    },
    "Sales Order": {
        "after_insert": "arnav_customization.shopify_order_patch.smart_sku_mapper"
    },
        "Sales Invoice": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.sales_invoice.process"
    },

    "Quotation": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.quotation.process"
    },

    "Debit Note": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.debit_note.process"
    },

    "Stock Entry": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.stock_entry.process"
    },

    "Credit Note": {
        "validate": "arnav_customization.sku_mapping_backend.handlers.credit_note.process"
    }
}

after_migrate = [
    "arnav_customization.patches.register_debit_note_return.execute"
]

override_whitelisted_methods = {
    "erpnext.controllers.queries.item_query":
        "arnav_customization.queries.purchase_item_query.purchase_item_query"
}
