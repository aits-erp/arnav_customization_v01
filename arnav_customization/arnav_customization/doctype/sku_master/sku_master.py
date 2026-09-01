import json
import re

import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils import getdate
from frappe.utils import flt
from frappe.utils import now_datetime

class SKUMaster(Document):
    def before_insert(self):
        # When SKU Master is amended from cancelled document,
        # do not carry old cancelled Stock Entry reference
        if self.amended_from:
            self.stock_entry = None

            for row in self.sku_details:
                row.sku = None
                row.old_sku_ref = None
                # An amended master must never overwrite the cancelled master's
                # breakup or reuse its immutable design-code assignment.
                row.breakup_ref = None
                row.design_code = None
    def validate(self):
        # self.validate_required_codes()

        total_out_weight = flt(self.net_quantiity)
        total_in_weight = sum(flt(row.gross_weight) for row in self.sku_details)

        if total_in_weight > total_out_weight:
            frappe.throw(
                f"""
                Total Gross Weight ({total_in_weight:.3f})
                cannot be greater than Net Quantity ({total_out_weight:.3f}).

                Please reduce the Gross Weight in SKU Details before saving.
                """
            )

    # def validate_required_codes(self):
    #     required_codes = {
    #         "Element Code": "element_code",
    #         "Set Code": "set_code",
    #         "Design Code": "design_code",
    #     }

    #     for row in self.sku_details:
    #         for label, fieldname in required_codes.items():
    #             if not str(row.get(fieldname) or "").strip():
    #                 frappe.throw(f"{label} is required in SKU Details row {row.idx}.")

    def on_submit(self):
        # Supplier-margin pricing is intentionally disabled. Selling Price is
        # retained as manually entered (or set by another approved process).
        # if not frappe.flags.in_import:
        #     self.apply_supplier_margin()
        self.create_repack_stock_entry()

    def before_submit(self):
        validate_design_codes_for_submission(self)

    def on_update_after_submit(self):
        for row in self.sku_details:
            if not row.sku or not frappe.db.exists("SKU", row.sku):
                continue

            frappe.db.set_value(
                "SKU",
                row.sku,
                {
                    "product": row.product,
                    "d_no": row.d_no,
                    "selling_price": row.selling_price,
                    "gross_weight": row.gross_weight,
                    "net_weight": row.net_weight,
                    "huid": row.huid,
                    "element_code": row.element_code,
                    "set_code": row.set_code,
                    "design_code": row.design_code,
                },
                update_modified=False,
            )
    def on_cancel(self):
        if getattr(self, "stock_entry", None):
            se = frappe.get_doc("Stock Entry", self.stock_entry)
            if se.docstatus == 1:
                se.cancel()

        # Keep generated records for auditability, but do not leave cancelled
        # physical SKUs selectable in POS or other SKU-driven workflows.
        for sku in frappe.get_all("SKU", filters={"sku_master": self.name}, pluck="name"):
            frappe.db.set_value("SKU", sku, "status", "Cancelled", update_modified=False)

        void_unshared_design_codes_for_cancelled_master(self)

    def create_repack_stock_entry(self):

        if getattr(self, "stock_entry", None):
            frappe.throw("Stock Entry already created against this SKU Master.")

        if not self.warehouse:
            frappe.throw("Warehouse is mandatory before submitting.")

        if not self.sku_details:
            frappe.throw("SKU Details are mandatory for Stock In process.")


        company = frappe.get_cached_value("Global Defaults", None, "default_company")
        if not company:
            frappe.throw("Default Company is not set in Global Defaults.")

        # ---------------------------------------------
        # CALCULATE TOTAL OUT WEIGHT (FROM NET QUANTITY)
        # ---------------------------------------------
        
        total_out_weight = flt(self.net_quantiity or 0)

        if total_out_weight <= 0:
            frappe.throw("Net Quantity must be greater than zero.")
        

        # total_out_weight = flt(self.net_quantiity)

        # if total_out_weight <= 0:
        #     frappe.throw("Net Quantity must be greater than zero.")

        # ---------------------------------------------
        # CALCULATE TOTAL IN WEIGHT (FROM SKU DETAILS)
        # ---------------------------------------------
        # total_in_weight = 0

        # for row in self.sku_details:
        #     if flt(row.gross_weight) <= 0:
        #         frappe.throw(f"Gross Weight must be greater than zero in row {row.idx}")

        #     total_in_weight += flt(row.gross_weight)

        # # ---------------------------------------------
        # # VALIDATION
        # # ---------------------------------------------
        # if total_in_weight > total_out_weight:
        #     frappe.throw(
        #         f"""
        #         Total SKU Gross Weight ({total_in_weight:.3f})
        #         cannot be greater than Net Quantity ({total_out_weight:.3f}).

        #         Please reduce the Gross Weight in SKU Details.
        #         """
        #     )


        # ---------------------------------------------
        # CALCULATE TOTAL IN WEIGHT (FROM SKU DETAILS)
        # ---------------------------------------------
        # total_in_weight = 0

        # for row in self.sku_details:
        #     if flt(row.gross_weight) <= 0:
        #         frappe.throw(f"Gross Weight must be greater than zero in row {row.idx}")
        #     total_in_weight += flt(row.gross_weight)

        # total_in_qty = 0

        # for row in self.sku_details:
        #     if flt(row.qty) <= 0:
        #         frappe.throw(f"Qty must be greater than zero in row {row.idx}")

        #     total_in_qty += flt(row.qty)

        # ---------------------------------------------
        # VALIDATION
        # ---------------------------------------------
        # if total_in_weight > total_out_weight:
        #     frappe.throw(
        #         f"""
        #         Total Finished Gross Weight ({total_in_weight})
        #         cannot exceed Available Gross Weight ({total_out_weight}).

        #         Please adjust SKU Gross Weight values.
        #         """
        #     )

        if not self.net_quantiity:
            frappe.throw("Gross weight must be entered.")

        for row in self.sku_details:
            if not row.product:
                frappe.throw(f"Product is missing in row {row.idx}")

            is_stock_item = frappe.db.get_value("Item", row.product, "is_stock_item")

            if not is_stock_item:
                frappe.throw(f"Item {row.product} is not marked as Stock Item (row {row.idx})")

            if flt(row.qty) <= 0:
                frappe.throw(f"Qty must be greater than zero in row {row.idx}")

            if flt(row.gross_weight) <= 0:
                frappe.throw(f"Gross weight must be entered in row {row.idx}")

            if not row.cost_price:
                frappe.throw(f"Cost Price is required for row {row.idx}")
        
        # ---------------------------------------------
        # CALCULATE ACTUAL ISSUE QTY
        # ---------------------------------------------
        # actual_out_qty = total_out_weight - total_in_weight
        # CALCULATE ACTUAL ISSUE QTY
        # actual_out_qty = total_in_weight
        
        actual_out_qty = total_out_weight

        if actual_out_qty <= 0:
            frappe.throw("Available gross weight must be greater than zero.")

        # ---------------------------------------------
        # CREATE STOCK ENTRY
        # ---------------------------------------------
        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Repack"
        se.company = company
        # se.posting_date = frappe.utils.nowdate()
        # se.posting_time = frappe.utils.nowtime()
        
        from frappe.utils import get_datetime

        # Single source of truth: SKU Master posting_date (Datetime)
        if not self.posting_date:
            frappe.throw("Posting Date is mandatory for Stock Entry")

        dt = get_datetime(self.posting_date)

        se.posting_date = dt.date()
        se.posting_time = dt.time()

        # -----------------------------
        # STOCK OUT (ISSUE)
        # -----------------------------
        remaining_issue_qty = actual_out_qty

        # Fetch the single selected Purchase Invoice
        pi = frappe.get_doc("Purchase Invoice", self.invoice_no)

        for item in pi.items:
            if not item.item_code:
                continue

            if remaining_issue_qty <= 0:
                break

            available_qty = flt(item.qty)

            if available_qty <= 0:
                continue

            issue_qty = min(available_qty, remaining_issue_qty)

            se.append("items", {
                "item_code": item.item_code,
                "qty": issue_qty,
                "s_warehouse": self.warehouse
            })

            remaining_issue_qty -= issue_qty

        if remaining_issue_qty > 0:
            frappe.throw("Not enough quantity in Purchase Invoice to complete repack.")

        # -----------------------------
        # STOCK IN (RECEIPT)
        # -----------------------------
        for row in self.sku_details:
            if not row.product:
                frappe.throw(f"Product is missing in row {row.idx}")

            if flt(row.qty) <= 0:
                frappe.throw(f"Qty must be greater than zero in row {row.idx}")

            if flt(row.gross_weight) <= 0:
                frappe.throw(f"Gross weight must be entered in row {row.idx}")

            if not row.breakup_ref:
                row.breakup_ref = frappe.generate_hash(length=12)

            # 1️⃣ Generate Batch Name
            batch_name = self.generate_custom_batch_name(self.date_of_invoice)

            # 2️⃣ Create Batch
            batch = frappe.new_doc("Batch")
            batch.batch_id = batch_name
            batch.item = row.product
            batch.insert(ignore_permissions=True)

            # 3️⃣ Store SKU in child row
            row.db_set("sku", batch_name)

            # 4️⃣ Create SKU Record
            sku_doc = frappe.new_doc("SKU")

            sku_doc.breakup_ref = row.breakup_ref
        
            sku_doc.sku_code = batch_name
            sku_doc.product = row.product
            sku_doc.element_code = row.element_code
            sku_doc.set_code = row.set_code
            sku_doc.design_code = row.design_code
            sku_doc.batch_no = batch_name
            sku_doc.warehouse = self.warehouse

            sku_doc.gross_weight = row.gross_weight
            sku_doc.net_weight = row.net_weight
            sku_doc.qty = row.qty

            sku_doc.d_no = row.d_no
            sku_doc.huid = row.huid

            sku_doc.cost_price = row.cost_price
            sku_doc.selling_price = row.selling_price

            sku_doc.shopify_rate = flt(row.shopify_rate)
            sku_doc.gst_percentage = flt(row.gst_percentage)
            sku_doc.gst_amount = flt(row.gst_amount)
            sku_doc.shopify_selling_rate = flt(row.shopify_selling_rate)

            sku_doc.image_url = row.image

            sku_doc.sku_master = self.name
            sku_doc.metal = self.metal
            sku_doc.supplier = self.supplier_name
            sku_doc.hsn = self.hsn

            sku_doc.status = "Available"
            sku_doc.valuation_rate = row.cost_price
            sku_doc.created_from_pi = self.invoice_no
            sku_doc.old_sku_ref = row.old_sku_ref
            sku_doc.supplier_invoice_no = self.supplier_invoice_no

            sku_doc.insert(ignore_permissions=True)

            if not row.cost_price:
                frappe.throw(f"Cost Price is required for row {row.idx}")

            #5️⃣ Add to Stock Entry
            se.append("items", {
                "item_code": row.product,
                # "qty": flt(row.gross_weight),
                "qty": flt(row.qty),
                "t_warehouse": self.warehouse,
                "batch_no": batch_name,
                # "is_finished_item": 1,
                "set_basic_rate_manually": 1,
                "basic_rate": flt(row.cost_price)
            })

        
        if not se.items:
            frappe.throw("No valid items found for Stock Entry.")

        for d in se.items:
            if not d.item_code:
                frappe.throw("Stock Entry has item with empty item_code")

        se.insert()
        se.submit()

        self.db_set("stock_entry", se.name)

        frappe.msgprint(
            msg="Stock Entry Created Successfully",
            title="Success",
            indicator="green"
        )
    
    def apply_supplier_margin(self):
        # Kept as an inert method so any legacy caller cannot overwrite a
        # manually entered Selling Price.
        #
        # if not self.supplier_name:
        #     frappe.throw("Supplier must be selected before calculating selling price.")
        #
        # margin = frappe.db.get_value(
        #     "Supplier",
        #     self.supplier_name,
        #     "custom_supplier_margin"
        # )
        #
        # for row in self.sku_details:
        #     row.selling_price = flt(row.cost_price) * flt(margin)
        return
            
    def generate_custom_batch_name(self, posting_date):
        from frappe.utils import getdate

        if not self.metal:
            frappe.throw("Metal must be selected before generating SKU.")

        if not self.supplier_name:
            frappe.throw("Supplier must be selected before generating SKU.")

        if not posting_date:
            frappe.throw("Date of Invoice is required for SKU generation.")

        posting_date = getdate(posting_date)

        # ----------------------------
        # 1️⃣ METAL CODE (1 digit)
        # ----------------------------
        metal_code = frappe.db.get_value(
            "Metal Master",
            self.metal,
            "metal_code"
        )

        if not metal_code:
            frappe.throw(f"Metal Code not defined for Metal {self.metal}")

        metal_code = str(metal_code)

        # ----------------------------
        # 2️⃣ SUPPLIER CODE (3 digit)
        # ----------------------------
        # Supplier ID is stored as document name
        supplier_code = str(self.supplier_name)

        # Force numeric and pad to 3 digits
        if not supplier_code.isdigit():
            frappe.throw(
                f"Supplier ID must be numeric to generate SKU. Found: {supplier_code}"
            )

        supplier_code = supplier_code.zfill(3)

        # ----------------------------
        # 3️⃣ YEAR (YY) + MONTH (MM)
        # ----------------------------
        year = posting_date.strftime("%y")
        month = posting_date.strftime("%m")

        # ----------------------------
        # 4️⃣ PREFIX BUILD
        # ----------------------------
        prefix = f"{metal_code}{year}{month}{supplier_code}"

        # ----------------------------
        # 5️⃣ GET LAST SEQUENCE SAFELY
        # ----------------------------
        last_batch = frappe.db.sql("""
            SELECT name FROM `tabBatch`
            WHERE name LIKE %s
            ORDER BY name DESC
            LIMIT 1
        """, (f"{prefix}%",), as_dict=True)

        if last_batch:
            last_sequence = int(last_batch[0]["name"][-4:])
            next_sequence = last_sequence + 1
        else:
            next_sequence = 1

        if next_sequence > 9999:
            frappe.throw(
                f"Monthly SKU limit exceeded for prefix {prefix}. Max 9999 reached."
            )

        sequence_str = str(next_sequence).zfill(4)

        return f"{prefix}{sequence_str}"
        
BREAKUP_FIELDS = [
    "attribute_type",
    "attribute_value",
    "weight",
    "price",
    "unit"
]

CLASSIFICATION_ATTRIBUTE_TYPES = ("SET_CODE", "ELEMENT_CODE")
CODE_VALUE_FIELDS = {
    "SET_CODE": "abbreviation",
    "ELEMENT_CODE": "abbreviation",
}


def _normalise_code(value, label):
    value = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9]+", value):
        frappe.throw(f"{label} must contain only uppercase letters and numbers.")
    return value


def _require_sku_master_write_permission(sku_master):
    if not frappe.has_permission("SKU Master", "write", sku_master):
        frappe.throw("You do not have permission to update this SKU Master.", frappe.PermissionError)


def _get_classification_from_rows(rows, require_complete=False):
    classification = {}

    for attribute_type in CLASSIFICATION_ATTRIBUTE_TYPES:
        values = [
            row.get("attribute_value")
            for row in rows
            if row.get("attribute_type") == attribute_type and row.get("attribute_value")
        ]

        if len(values) > 1:
            frappe.throw(f"Only one {attribute_type.replace('_', ' ').title()} is allowed per breakup.")

        if values:
            classification[attribute_type] = values[0]

    if require_complete and len(classification) != len(CLASSIFICATION_ATTRIBUTE_TYPES):
        frappe.throw("Set Code and Element Code are required before generating a Design Code.")

    return classification


def _get_classification_values(classification):
    values = {}
    for attribute_type, document_name in classification.items():
        fieldname = CODE_VALUE_FIELDS[attribute_type]
        value = frappe.db.get_value(attribute_type, document_name, fieldname)
        if not value:
            frappe.throw(
                f"{attribute_type.replace('_', ' ').title()} '{document_name}' needs an Abbreviation before a Design Code can be generated."
            )
        values[attribute_type] = _normalise_code(value, attribute_type.replace("_", " ").title())
    return values


def _get_design_code_for_breakup(sku_master, breakup_ref):
    if not breakup_ref:
        return None

    design_code = frappe.db.get_value(
        "SKU Details",
        {"parent": sku_master, "breakup_ref": breakup_ref},
        "design_code",
    )
    if design_code:
        return design_code

    return frappe.db.get_value(
        "SKU",
        {"sku_master": sku_master, "breakup_ref": breakup_ref},
        "design_code",
    )


def _set_design_code_for_breakup(sku_master, breakup_ref, design_code):
    sku_detail_names = frappe.get_all(
        "SKU Details",
        filters={"parent": sku_master, "breakup_ref": breakup_ref},
        pluck="name",
    )
    sku_names = frappe.get_all(
        "SKU",
        filters={"sku_master": sku_master, "breakup_ref": breakup_ref},
        pluck="name",
    )

    if not sku_detail_names and not sku_names:
        frappe.throw("This breakup is not linked to a SKU Details row or SKU record.")

    for name in sku_detail_names:
        frappe.db.set_value("SKU Details", name, "design_code", design_code, update_modified=False)

    for name in sku_names:
        frappe.db.set_value("SKU", name, "design_code", design_code, update_modified=False)


def _has_design_code_assignment_target(sku_master, breakup_ref):
    return bool(
        frappe.db.exists("SKU Details", {"parent": sku_master, "breakup_ref": breakup_ref})
        or frappe.db.exists("SKU", {"sku_master": sku_master, "breakup_ref": breakup_ref})
    )


def _get_design_code_doc(design_code):
    if not design_code or not frappe.db.exists("Design Code", design_code):
        frappe.throw("The assigned Design Code registry entry is missing.")
    return frappe.get_doc("Design Code", design_code)


def _validate_design_code_matches_classification(design_code, classification):
    design = _get_design_code_doc(design_code)
    values = _get_classification_values(classification)

    if design.status != "Active":
        frappe.throw(f"Design Code {design_code} is {design.status} and cannot be assigned.")

    if design.set_code != classification["SET_CODE"] or design.element_code != classification["ELEMENT_CODE"]:
        frappe.throw(f"Design Code {design_code} does not match this breakup's Set Code and Element Code.")

    if (
        design.set_code_value != values["SET_CODE"]
        or design.element_code_value != values["ELEMENT_CODE"]
    ):
        frappe.throw(f"Design Code {design_code} no longer matches the configured master-code values.")

    return design


def _ensure_locked_classification_is_unchanged(sku_master, breakup_ref, rows):
    design_code = _get_design_code_for_breakup(sku_master, breakup_ref)
    if not design_code:
        return

    classification = _get_classification_from_rows(rows, require_complete=True)
    _validate_design_code_matches_classification(design_code, classification)


def _get_active_design_code_count_outside_master(design_code, sku_master):
    return frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabSKU Details` AS sku_detail
        INNER JOIN `tabSKU Master` AS sku_master
            ON sku_master.name = sku_detail.parent
        WHERE sku_detail.design_code = %s
          AND sku_master.docstatus != 2
          AND sku_detail.parent != %s
        """,
        (design_code, sku_master),
    )[0][0]


def _get_active_design_code_count_outside_breakup(design_code, sku_master, breakup_ref):
    return frappe.db.sql(
        """
        SELECT COUNT(*)
        FROM `tabSKU Details` AS sku_detail
        INNER JOIN `tabSKU Master` AS sku_master
            ON sku_master.name = sku_detail.parent
        WHERE sku_detail.design_code = %s
          AND sku_master.docstatus != 2
          AND NOT (sku_detail.parent = %s AND sku_detail.breakup_ref = %s)
        """,
        (design_code, sku_master, breakup_ref),
    )[0][0]


def _void_design_code(design_code, reason):
    design = _get_design_code_doc(design_code)
    if design.status == "Voided":
        return

    design.status = "Voided"
    design.void_reason = reason
    design.voided_on = now_datetime()
    design.save(ignore_permissions=True)


def void_unshared_design_codes_for_cancelled_master(sku_master_doc):
    design_codes = {row.design_code for row in sku_master_doc.sku_details if row.design_code}
    for design_code in design_codes:
        if not frappe.db.exists("Design Code", design_code):
            continue
        if not _get_active_design_code_count_outside_master(design_code, sku_master_doc.name):
            _void_design_code(design_code, "SKU Master cancelled")


def validate_design_codes_for_submission(sku_master_doc):
    for row in sku_master_doc.sku_details:
        if not row.breakup_ref:
            frappe.throw(f"Breakup is required before submitting SKU Details row {row.idx}.")

        design_code = _get_design_code_for_breakup(sku_master_doc.name, row.breakup_ref) or row.design_code
        if not design_code:
            frappe.throw(f"Generate a Design Code before submitting SKU Details row {row.idx}.")

        breakup_rows = get_breakup_rows_for_reference(sku_master_doc.name, row.breakup_ref)
        classification = _get_classification_from_rows(breakup_rows, require_complete=True)
        _validate_design_code_matches_classification(design_code, classification)
        row.design_code = design_code

def _resolve_breakup_ref(sku_master, breakup_ref):
    if breakup_ref and frappe.db.exists("SKU Breakup", {
        "sku_master": sku_master,
        "breakup_ref": breakup_ref
    }):
        return breakup_ref

    refs = frappe.get_all(
        "SKU Breakup",
        filters={"sku_master": sku_master},
        fields=["breakup_ref"]
    )
    refs = {row.breakup_ref for row in refs if row.breakup_ref}

    # Safe recovery for old single-item masters whose saved ref became stale.
    if len(refs) == 1 and frappe.db.count(
        "SKU Details", {"parent": sku_master}
    ) == 1:
        return refs.pop()

    return breakup_ref


def get_breakup_rows_for_reference(sku_master, breakup_ref):
    resolved_ref = _resolve_breakup_ref(sku_master, breakup_ref)
    rows = []

    if resolved_ref:
        rows = frappe.get_all(
            "SKU Breakup",
            filters={
                "sku_master": sku_master,
                "breakup_ref": resolved_ref
            },
            fields=BREAKUP_FIELDS,
            order_by="creation asc"
        )

    if not rows and breakup_ref:
        # Legacy rows may contain the right ref but the wrong master link.
        rows = frappe.get_all(
            "SKU Breakup",
            filters={"breakup_ref": breakup_ref},
            fields=BREAKUP_FIELDS,
            order_by="creation asc"
        )

    return rows


@frappe.whitelist()
def get_breakup_rows(sku_master, breakup_ref):
    return get_breakup_rows_for_reference(sku_master, breakup_ref)


@frappe.whitelist()
def get_all_breakup_rows(sku_master):
    return frappe.get_all(
        "SKU Breakup",
        filters={"sku_master": sku_master},
        fields=["breakup_ref", *BREAKUP_FIELDS],
        order_by="breakup_ref asc, creation asc",
    )


@frappe.whitelist()
def get_breakup_design_state(sku_master, breakup_ref):
    breakup_ref = _resolve_breakup_ref(sku_master, breakup_ref)
    rows = get_breakup_rows_for_reference(sku_master, breakup_ref)
    classification = _get_classification_from_rows(rows)
    values = _get_classification_values(classification) if classification else {}
    design_code = _get_design_code_for_breakup(sku_master, breakup_ref)

    return {
        "breakup_ref": breakup_ref,
        "design_code": design_code,
        "classification_locked": bool(design_code),
        "set_code": classification.get("SET_CODE"),
        "set_code_value": values.get("SET_CODE"),
        "element_code": classification.get("ELEMENT_CODE"),
        "element_code_value": values.get("ELEMENT_CODE"),
        "can_generate": len(classification) == len(CLASSIFICATION_ATTRIBUTE_TYPES) and not design_code,
    }


def _get_design_code_sequence(design_code):
    return int(design_code.rsplit("-", 1)[1])


def _validate_breakup_can_be_assigned(sku_master, breakup_ref):
    if not sku_master or not frappe.db.exists("SKU Master", sku_master):
        frappe.throw("A saved SKU Master is required before assigning a Design Code.")

    sku_master_doc = frappe.get_doc("SKU Master", sku_master)
    if sku_master_doc.docstatus == 2:
        frappe.throw("A Design Code cannot be assigned to a cancelled SKU Master.")

    rows = get_breakup_rows_for_reference(sku_master, breakup_ref)
    classification = _get_classification_from_rows(rows, require_complete=True)
    if not _has_design_code_assignment_target(sku_master, breakup_ref):
        frappe.throw("This breakup is not linked to a SKU Details row or SKU record.")
    return classification


@frappe.whitelist()
def generate_design_code(sku_master, breakup_ref):
    _require_sku_master_write_permission(sku_master)
    breakup_ref = _resolve_breakup_ref(sku_master, breakup_ref)
    assigned_design_code = _get_design_code_for_breakup(sku_master, breakup_ref)
    if assigned_design_code:
        return {"design_code": assigned_design_code, "already_assigned": True}

    classification = _validate_breakup_can_be_assigned(sku_master, breakup_ref)
    values = _get_classification_values(classification)
    generated_design_code = make_autoname(
        f"{values['SET_CODE']}-{values['ELEMENT_CODE']}-.####"
    )

    design = frappe.new_doc("Design Code")
    design.design_code = generated_design_code
    design.status = "Active"
    design.set_code = classification["SET_CODE"]
    design.set_code_value = values["SET_CODE"]
    design.element_code = classification["ELEMENT_CODE"]
    design.element_code_value = values["ELEMENT_CODE"]
    design.sequence_no = _get_design_code_sequence(generated_design_code)
    design.created_from_sku_master = sku_master
    design.created_from_breakup_ref = breakup_ref
    design.insert(ignore_permissions=True)

    _set_design_code_for_breakup(sku_master, breakup_ref, generated_design_code)
    return {"design_code": generated_design_code, "already_assigned": False}


@frappe.whitelist()
def assign_existing_design_code(sku_master, breakup_ref, design_code):
    _require_sku_master_write_permission(sku_master)
    breakup_ref = _resolve_breakup_ref(sku_master, breakup_ref)
    if _get_design_code_for_breakup(sku_master, breakup_ref):
        frappe.throw("Correct the existing Design Code assignment before assigning another one.")

    classification = _validate_breakup_can_be_assigned(sku_master, breakup_ref)
    _validate_design_code_matches_classification(design_code, classification)
    _set_design_code_for_breakup(sku_master, breakup_ref, design_code)
    return {"design_code": design_code}


@frappe.whitelist()
def release_design_code_assignment(sku_master, breakup_ref, reason):
    _require_sku_master_write_permission(sku_master)
    if not (reason or "").strip():
        frappe.throw("A correction reason is required.")

    sku_master_doc = frappe.get_doc("SKU Master", sku_master)
    if sku_master_doc.docstatus != 0:
        frappe.throw("Cancel and amend the SKU Master before correcting an assigned Design Code.")

    breakup_ref = _resolve_breakup_ref(sku_master, breakup_ref)
    design_code = _get_design_code_for_breakup(sku_master, breakup_ref)
    if not design_code:
        frappe.throw("There is no Design Code assignment to correct.")

    _set_design_code_for_breakup(sku_master, breakup_ref, None)
    if not _get_active_design_code_count_outside_breakup(design_code, sku_master, breakup_ref):
        _void_design_code(design_code, f"Classification correction: {reason.strip()}")

    return {"design_code": None, "classification_locked": False}


@frappe.whitelist()
def save_breakup_rows(sku_master, breakup_ref, rows):
    _require_sku_master_write_permission(sku_master)
    rows = json.loads(rows)
    requested_ref = breakup_ref
    breakup_ref = _resolve_breakup_ref(sku_master, breakup_ref)
    breakup_ref = breakup_ref or frappe.generate_hash(length=12)

    # Once a code is assigned, only its two classification values are immutable.
    # The remaining breakup details can still be edited freely.
    _ensure_locked_classification_is_unchanged(sku_master, breakup_ref, rows)

    # delete old rows
    frappe.db.delete("SKU Breakup", {
        "sku_master": sku_master,
        "breakup_ref": breakup_ref
    })

    meta = frappe.get_meta("SKU Breakup")

    for r in rows:
        doc = frappe.new_doc("SKU Breakup")
        doc.sku_master = sku_master
        doc.breakup_ref = breakup_ref

        for df in meta.fields:
            fname = df.fieldname
            if fname in ["sku_master", "breakup_ref"]:
                continue
            if fname in r:
                doc.set(fname, r.get(fname))

        doc.insert(ignore_permissions=True)

    # Repair stale references after safely resolving an old single-item master.
    if requested_ref and requested_ref != breakup_ref:
        for child in frappe.get_all(
            "SKU Details",
            filters={"parent": sku_master, "breakup_ref": requested_ref},
            pluck="name"
        ):
            frappe.db.set_value("SKU Details", child, "breakup_ref", breakup_ref)

        for sku in frappe.get_all(
            "SKU",
            filters={"sku_master": sku_master, "breakup_ref": requested_ref},
            pluck="name"
        ):
            frappe.db.set_value("SKU", sku, "breakup_ref", breakup_ref)

    return {
        "breakup_ref": breakup_ref,
        "rows": get_breakup_rows_for_reference(sku_master, breakup_ref),
        "design_state": get_breakup_design_state(sku_master, breakup_ref),
    }


