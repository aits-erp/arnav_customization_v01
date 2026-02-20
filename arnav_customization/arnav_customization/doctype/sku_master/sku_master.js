frappe.ui.form.on("SKU Master", {
        refresh(frm) {
        frm.add_custom_button(
            __("Get Items From"),
            () => open_multi_invoice_dialog(frm)
        );
    }
});

function calculate_weight_totals(frm) {

    let total_net = 0;
    let total_gross = 0;

    (frm.doc.sku_details || []).forEach(row => {
        total_net += flt(row.net_weight);
        total_gross += flt(row.gross_weight);
    });

    frm.set_value("total_net_weight", total_net);
    frm.set_value("total_gross_weight", total_gross);

    frm.refresh_fields([
        "total_net_weight",
        "total_gross_weight"
    ]);
}

function open_multi_invoice_dialog(frm) {
    new frappe.ui.form.MultiSelectDialog({
        doctype: "Purchase Invoice",
        target: frm,
        setters: {
            supplier: null,
            posting_date: null
        },
        add_filters_group: 1,
        date_field: "posting_date",
        get_query() {
            return { filters: { docstatus: 1 } };
        },
        action(selections) {
            if (!selections.length) return;

            frappe.confirm(
                __("Replace existing items? Click No to Append."),
                () => load_invoices(frm, selections, true),
                () => load_invoices(frm, selections, false)
            );
        }
    });
}

function load_invoices(frm, invoice_names, replace) {

    if (!invoice_names || !invoice_names.length) return;

    // Always take ONLY the first invoice (client requirement)
    const first_invoice = invoice_names[0];

    // Since only single invoice allowed, clear table
    frm.clear_table("purchase_invoices");

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Purchase Invoice",
            name: first_invoice
        },
        callback(r) {
            if (!r.message) return;

            const inv = r.message;

            // -----------------------------
            // 1️⃣ Add Purchase Invoice row
            // -----------------------------
            const inv_row = frm.add_child("purchase_invoices");
            inv_row.purchase_invoice = inv.name;
            inv_row.supplier = inv.supplier;
            inv_row.posting_date = inv.posting_date;

            frm.refresh_field("purchase_invoices");

            // -----------------------------
            // 2️⃣ Fetch Header Fields
            // -----------------------------
            frm.set_value("supplier_name", inv.supplier);
            frm.set_value("invoice_no", inv.name);
            frm.set_value("date_of_invoice", inv.posting_date);
            frm.set_value("warehouse", inv.set_warehouse || inv.items?.[0]?.warehouse || "");
            frm.set_value("metal", inv.metal || "");
            frm.set_value("hsn", inv.hsn || "");

            // -----------------------------
            // 3️⃣ Calculate Net Quantity
            // -----------------------------
            let total_qty = 0;

            (inv.items || []).forEach(item => {
                total_qty += flt(item.qty);
            });

            frm.set_value("net_quantiity", total_qty);

            // -----------------------------
            // 4️⃣ Refresh Header Fields
            // -----------------------------
            frm.refresh_fields([
                "supplier_name",
                "invoice_no",
                "date_of_invoice",
                "warehouse",
                "metal",
                "hsn",
                "net_quantiity"
            ]);
        }
    });
}


function finalize_form(frm, suppliers, total_qty) {
    frm.set_value("net_quantiity", total_qty);

    if (suppliers.size === 1) {
        frm.set_value("supplier_name", [...suppliers][0]);
    } else {
        frm.set_value("supplier_name", __("Multiple Suppliers"));
    }

    // ONE authoritative refresh
    frm.refresh_field("purchase_invoices");
    frm.refresh_field("sku_details");
    frm.refresh_field("net_quantiity");
    frm.refresh_field("supplier_name");
}

//BREAK UP TABLE SYNC PLUS DYANMIC BEHAVIOUR
frappe.ui.form.on("SKU Details", {

    net_weight(frm, cdt, cdn) {
        calculate_weight_totals(frm);
    },

    gross_weight(frm, cdt, cdn) {
        calculate_weight_totals(frm);
    },

    sku_details_remove(frm) {
        calculate_weight_totals(frm);
    },

    breakup(frm, cdt, cdn) {
        let row = locals[cdt][cdn];

        if (!row.breakup_ref) {
            row.breakup_ref = frappe.utils.get_random(12);
            frm.refresh_field("sku_details");
        }

        if (frm.is_new()) {
            frappe.msgprint({
                title: "Save Required",
                message: "You must save the SKU Master before adding Breakup details.",
                indicator: "orange"
            });
            return;
        }

        open_dynamic_breakup_dialog(frm, row);
    },

    cost_price(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!frm.doc.supplier_name) {
            frappe.msgprint({
                title: "Supplier Required",
                message: "Please select Supplier before entering Cost Price.",
                indicator: "orange"
            });
            return;
        }

        frappe.db.get_value("Supplier", frm.doc.supplier_name, "custom_supplier_margin")
            .then(r => {

                let margin = flt(r.message.custom_supplier_margin || 0);

                if (!margin) {
                    frappe.msgprint({
                        title: "Supplier Margin Missing",
                        message: "Supplier Margin is not defined for selected Supplier.",
                        indicator: "red"
                    });
                    return;
                }

                row.selling_price = flt(row.cost_price) * margin;
                frm.refresh_field("sku_details");
            });
    } 
    
});




function open_dynamic_breakup_dialog(frm, row) {

    frappe.call({
        method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.get_breakup_meta",
        callback(meta_res) {

            let dynamic_fields = meta_res.message || [];

            let dialog = new frappe.ui.Dialog({
                title: "Breakup - " + (row.product || ""),
                size: "extra-large",
                fields: [
                    {
                        fieldname: "breakup_table",
                        fieldtype: "Table",
                        label: "Breakup Details",
                        in_place_edit: true,
                        cannot_add_rows: false,
                        data: [],
                        get_data: () => {
                            return dialog.fields_dict.breakup_table.df.data;
                        },
                        fields: dynamic_fields
                    }
                ],
                primary_action_label: "Save",
                primary_action(values) {

                    let rows = values.breakup_table || [];

                    frappe.call({
                        method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.save_breakup_rows",
                        args: {
                            sku_master: frm.doc.name,
                            breakup_ref: row.breakup_ref,
                            rows: JSON.stringify(rows)
                        },
                        callback() {
                            frappe.msgprint("Breakup saved successfully");
                            dialog.hide();
                        }
                    });
                }
            });

            // Load existing rows
            frappe.call({
                method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.get_breakup_rows",
                args: {
                    sku_master: frm.doc.name,
                    breakup_ref: row.breakup_ref
                },
                callback(r) {
                    if (r.message) {
                        dialog.fields_dict.breakup_table.df.data = r.message;
                        let grid = dialog.fields_dict.breakup_table.grid;
                        grid.refresh();
                        // grid.wrapper.find('.grid-body').css({
                        //     'overflow-X': 'auto',
                        //     'white-space': 'nowrap'
                        // });
                        let grid_wrapper = dialog.fields_dict.breakup_table.grid.wrapper;

                        grid_wrapper.css({
                            "min-width": "max-content"
                        });

                        grid_wrapper.find(".grid-body").css({
                            "overflow-x": "auto"
                        });
                    }
                }
            });

            dialog.show();
            setTimeout(() => {

                // Increase modal width
                dialog.$wrapper.find('.modal-dialog').css({
                    "max-width": "95vw",
                    "width": "95vw"
                });

                // Increase modal height
                dialog.$wrapper.find('.modal-content').css({
                    "height": "90vh"
                });

                // Allow modal body to scroll normally
                dialog.$wrapper.find('.modal-body').css({
                    "overflow-y": "auto",
                    "overflow-x": "auto",
                    "height": "80vh"
                });

                // VERY IMPORTANT: allow dropdown to overflow grid
                dialog.$wrapper.find('.grid-body').css({
                    "overflow": "visible"
                });

            }, 200);


        }
    });
}

