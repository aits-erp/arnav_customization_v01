import erpnext.controllers.sales_and_purchase_return as spr

def execute():
    spr.return_against_item_fields["Debit Note"] = "purchase_invoice_item"