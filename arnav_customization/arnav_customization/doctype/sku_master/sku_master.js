frappe.ui.form.on("SKU Master", {

    invoice_no: function(frm) {

        if (!frm.doc.invoice_no) {

            frm.set_value("supplier_name", "");
            frm.set_value("metal", "");
            frm.set_value("hsn", "");
            frm.set_value("date_of_invoice", "");
            frm.set_value("warehouse", "");
            frm.set_value("net_quantiity", "");

            return;
        }

        load_invoices(frm, [frm.doc.invoice_no], true);
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

// function load_invoices(frm, invoice_names, replace) {

//     if (!invoice_names || !invoice_names.length) return;

//     // Always take ONLY the first invoice (client requirement)
//     const first_invoice = invoice_names[0];

//     frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: "Purchase Invoice",
//             name: first_invoice
//         },
//         callback(r) {
//             if (!r.message) return;

//             const inv = r.message;

//             // -----------------------------
//             // 1️⃣ Add Purchase Invoice row
//             // -----------------------------
//             const inv_row = frm.add_child("purchase_invoices");
//             inv_row.purchase_invoice = inv.name;
//             inv_row.supplier = inv.supplier;
//             inv_row.posting_date = inv.posting_date;

//             frm.refresh_field("purchase_invoices");

//             // -----------------------------
//             // 2️⃣ Fetch Header Fields (Safe Version)
//             // -----------------------------

//             frm.set_value("supplier_name", inv.supplier || "");
//             frm.set_value("invoice_no", inv.name || "");
//             frm.set_value("date_of_invoice", inv.posting_date || "");
//             frm.set_value("warehouse", inv.set_warehouse || inv.items?.[0]?.warehouse || "");

//             // -----------------------------
//             // ✅ Metal (Safe Handling)
//             // -----------------------------
//             if ("custom_metal" in inv) {
//                 frm.set_value("metal", inv.custom_metal || "");
//             } else {
//                 console.warn("custom_metal field not found in Purchase Invoice");
//                 frm.set_value("metal", "");
//             }

//             // -----------------------------
//             // ✅ HSN From Item Master (Safe Handling)
//             // -----------------------------

//             frm.set_value("hsn", "");  // clear first

//             if (inv.items && inv.items.length > 0) {

//                 let first_item = inv.items[0].item_code;

//                 if (!first_item) {
//                     console.warn("First item has no item_code");
//                     return;
//                 }

//                 frappe.db.get_value("Item", first_item, "gst_hsn_code")
//                     .then(res => {

//                         if (res && res.message && res.message.gst_hsn_code) {
//                             frm.set_value("hsn", res.message.gst_hsn_code);
//                         } else {
//                             console.warn("gst_hsn_code not found on Item:", first_item);
//                             frm.set_value("hsn", "");
//                         }

//                     })
//                     .catch(err => {
//                         console.error("Error fetching gst_hsn_code:", err);
//                         frm.set_value("hsn", "");
//                     });

//             } else {
//                 console.warn("No items found in Purchase Invoice:", inv.name);
//             }

//             // -----------------------------
//             // 3️⃣ Calculate Net Quantity
//             // -----------------------------
//             let total_qty = 0;

//             (inv.items || []).forEach(item => {
//                 total_qty += flt(item.qty);
//             });

//             frm.set_value("net_quantiity", total_qty);

//             // -----------------------------
//             // 4️⃣ Refresh Header Fields
//             // -----------------------------
//             frm.refresh_fields([
//                 "supplier_name",
//                 "invoice_no",
//                 "date_of_invoice",
//                 "warehouse",
//                 "metal",
//                 "hsn",
//                 "net_quantiity"
//             ]);
//         }
//     });
// }
function load_invoices(frm, invoice_names, replace) {

    if (!invoice_names || !invoice_names.length) return;

    const first_invoice = invoice_names[0];

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
            // 1️⃣ Fetch Header Fields
            // -----------------------------

            frm.set_value("supplier_name", inv.supplier || "");
            frm.set_value("invoice_no", inv.name || "");
            frm.set_value("date_of_invoice", inv.posting_date || "");
            frm.set_value("warehouse", inv.set_warehouse || inv.items?.[0]?.warehouse || "");

            // -----------------------------
            // ✅ Metal (Safe Handling)
            // -----------------------------
            if ("custom_metal" in inv) {
                frm.set_value("metal", inv.custom_metal || "");
            } else {
                console.warn("custom_metal field not found in Purchase Invoice");
                frm.set_value("metal", "");
            }

            // -----------------------------
            // ✅ HSN From Item Master
            // -----------------------------

            frm.set_value("hsn", "");

            if (inv.items && inv.items.length > 0) {

                let first_item = inv.items[0].item_code;

                if (!first_item) {
                    console.warn("First item has no item_code");
                } else {

                    frappe.db.get_value("Item", first_item, "gst_hsn_code")
                        .then(res => {

                            if (res && res.message && res.message.gst_hsn_code) {
                                frm.set_value("hsn", res.message.gst_hsn_code);
                            } else {
                                console.warn("gst_hsn_code not found on Item:", first_item);
                                frm.set_value("hsn", "");
                            }

                        })
                        .catch(err => {
                            console.error("Error fetching gst_hsn_code:", err);
                            frm.set_value("hsn", "");
                        });
                }
            }

            // -----------------------------
            // 2️⃣ Calculate Net Quantity
            // -----------------------------

            let total_qty = 0;

            (inv.items || []).forEach(item => {
                total_qty += flt(item.qty);
            });

            frm.set_value("net_quantiity", total_qty);

            // -----------------------------
            // 3️⃣ Refresh Fields
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

    let dynamic_fields = [
        {
            fieldname: "attribute_type",
            label: "Attribute Type",
            fieldtype: "Select",
            options: `
COLLECTION
PRIMARY_STONE_TYPE
STONE_CUT
STONE_COLOUR
STONE_CLARITY
METAL_FINISH
DESIGN_STYLE
CULTURAL_STYLE
PRIMARY_OCCASION
AESTHETIC`,
            in_list_view: 1
        },
        {
            fieldname: "attribute_value",
            label: "Attribute Value",
            fieldtype: "Link",
            options: "",   // will set dynamically
            in_list_view: 1
        },
        {
            fieldname: "weight",
            label: "Weight",
            fieldtype: "Float",
            in_list_view: 1
        },
        {
            fieldname: "price",
            label: "Price",
            fieldtype: "Float",
            in_list_view: 1
        },
        {
            fieldname: "unit",
            label: "Unit",
            fieldtype: "Data",
            in_list_view: 1
        }
    ];

    frappe.call({
        method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.get_breakup_rows",
        args: {
            sku_master: frm.doc.name,
            breakup_ref: row.breakup_ref
        },
        callback: function(r) {

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
                        data: r.message || [],
                        fields: dynamic_fields
                    }
                ],
                primary_action_label: "Save",
                primary_action(values) {

                    frappe.call({
                        method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.save_breakup_rows",
                        args: {
                            sku_master: frm.doc.name,
                            breakup_ref: row.breakup_ref,
                            rows: JSON.stringify(values.breakup_table || [])
                        },
                        callback() {
                            frappe.msgprint("Breakup saved successfully");
                            dialog.hide();
                        }
                    });
                }
            });

            dialog.show();

            let grid = dialog.fields_dict.breakup_table.grid;

            // 🔥 CRITICAL PART — set doctype before dropdown opens
            grid.wrapper.on("focus", "input[data-fieldname='attribute_value']", function () {

                let grid_row = $(this).closest(".grid-row").data("grid_row");
                if (!grid_row) return;

                let row_doc = grid_row.doc;
                if (!row_doc.attribute_type) return;

                grid.update_docfield_property(
                    "attribute_value",
                    "options",
                    row_doc.attribute_type
                );
            });

        }
    });
}


// frappe.ui.form.on("SKU Master", {
//         refresh(frm) {
//         frm.add_custom_button(
//             __("Get Items From"),
//             () => open_multi_invoice_dialog(frm)
//         );
//     }
// });

// function open_multi_invoice_dialog(frm) {
//     new frappe.ui.form.MultiSelectDialog({
//         doctype: "Purchase Invoice",
//         target: frm,
//         setters: {
//             supplier: null,
//             posting_date: null
//         },
//         add_filters_group: 1,
//         date_field: "posting_date",
//         get_query() {
//             return { filters: { docstatus: 1 } };
//         },
//         action(selections) {
//             if (!selections.length) return;

//             frappe.confirm(
//                 __("Replace existing items? Click No to Append."),
//                 () => load_invoices(frm, selections, true),
//                 () => load_invoices(frm, selections, false)
//             );
//         }
//     });
// }

// function open_dynamic_breakup_dialog(frm, row) {

//     frappe.call({
//         method: "frappe.client.get",
//         args: {
//             doctype: "DocType",
//             name: "SKU Breakup"
//         },
//         callback: function(meta_res) {

//             let meta_fields = meta_res.message.fields;

//             // Remove system fields
//             let filtered_fields = meta_fields.filter(df =>
//                 ![
//                     "sku_master",
//                     "breakup_ref",
//                     "name",
//                     "owner",
//                     "creation",
//                     "modified",
//                     "modified_by",
//                     "docstatus",
//                     "idx"
//                 ].includes(df.fieldname)
//             );

//             // Load existing rows
//             frappe.call({
//                 method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.get_breakup_rows",
//                 args: {
//                     sku_master: frm.doc.name,
//                     breakup_ref: row.breakup_ref
//                 },
//                 callback: function(r) {

//                     let dialog = new frappe.ui.Dialog({
//                         title: "Breakup - " + (row.product || ""),
//                         size: "extra-large",
//                         fields: [
//                             {
//                                 fieldname: "breakup_table",
//                                 fieldtype: "Table",
//                                 label: "Breakup Details",
//                                 in_place_edit: true,
//                                 cannot_add_rows: false,
//                                 data: r.message || [],
//                                 fields: filtered_fields
//                             }
//                         ],
//                         primary_action_label: "Save",
//                         primary_action(values) {

//                             frappe.call({
//                                 method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.save_breakup_rows",
//                                 args: {
//                                     sku_master: frm.doc.name,
//                                     breakup_ref: row.breakup_ref,
//                                     rows: JSON.stringify(values.breakup_table || [])
//                                 },
//                                 callback() {
//                                     frappe.msgprint("Breakup saved successfully");
//                                     dialog.hide();
//                                 }
//                             });
//                         }
//                     });

//                     dialog.show();
//                     let grid = dialog.fields_dict.breakup_table.grid;

//                     grid.wrapper.on("focus", "input[data-fieldname='attribute_value']", function () {

//                         let grid_row = $(this).closest(".grid-row").data("grid_row");
//                         if (!grid_row) return;

//                         let row_doc = grid_row.doc;
//                         if (!row_doc.attribute_type) return;

//                         // Dynamically switch doctype before dropdown opens
//                         grid.update_docfield_property(
//                             "attribute_value",
//                             "options",
//                             row_doc.attribute_type
//                         );
//                     });
//                 }
//             });

//         }
//     });
// }

// function open_dynamic_breakup_dialog(frm, row) {

//     let dynamic_fields = [
//         {
//             fieldname: "attribute_type",
//             label: "Attribute Type",
//             fieldtype: "Select",
//             options: `
// COLLECTION
// PRIMARY_STONE_TYPE
// STONE_CUT
// STONE_COLOUR
// STONE_CLARITY
// METAL_FINISH
// DESIGN_STYLE
// CULTURAL_STYLE
// PRIMARY_OCCASION
// AESTHETIC`,
//             in_list_view: 1
//         },
//         {
//             fieldname: "attribute_value",
//             label: "Attribute Value",
//             fieldtype: "Link",
//             options: "",
//             in_list_view: 1
//         }
//     ];

//     let dialog = new frappe.ui.Dialog({
//         title: "Breakup - " + (row.product || ""),
//         size: "extra-large",
//         fields: [
//             {
//                 fieldname: "breakup_table",
//                 fieldtype: "Table",
//                 label: "Breakup Details",
//                 in_place_edit: true,
//                 cannot_add_rows: false,
//                 data: [],
//                 fields: dynamic_fields
//             }
//         ],
//         primary_action_label: "Save",
//         primary_action(values) {

//             frappe.call({
//                 method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.save_breakup_rows",
//                 args: {
//                     sku_master: frm.doc.name,
//                     breakup_ref: row.breakup_ref,
//                     rows: JSON.stringify(values.breakup_table || [])
//                 },
//                 callback() {
//                     frappe.msgprint("Breakup saved successfully");
//                     dialog.hide();
//                 }
//             });
//         }
//     });

//     dialog.show();

//     let grid = dialog.fields_dict.breakup_table.grid;

//     // 🔥 CORRECT WAY TO ACCESS ROW IN DIALOG GRID
//     grid.wrapper.on("focus", "input[data-fieldname='attribute_value']", function () {

//         let grid_row = $(this).closest(".grid-row").data("grid_row");

//         if (!grid_row) return;

//         let row_doc = grid_row.doc;

//         if (!row_doc.attribute_type) return;

//         // Set correct doctype before dropdown opens
//         grid.update_docfield_property(
//             "attribute_value",
//             "options",
//             row_doc.attribute_type
//         );
//     });

// }
