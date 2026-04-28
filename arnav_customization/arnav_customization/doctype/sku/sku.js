frappe.ui.form.on("SKU", {

    refresh(frm) {
        // Optional: show button only if breakup exists
        if (!frm.doc.breakup_ref) {
            frm.toggle_display("breakup_info", false);
        } else {
            frm.toggle_display("breakup_info", true);
        }
    },

    breakup_info(frm) {

        if (!frm.doc.breakup_ref) {
            frappe.msgprint("No breakup data found for this SKU.");
            return;
        }

        if (!frm.doc.sku_master) {
            frappe.msgprint("SKU Master reference missing.");
            return;
        }

        frappe.call({
            method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.get_breakup_rows",
            args: {
                sku_master: frm.doc.sku_master,
                breakup_ref: frm.doc.breakup_ref
            },
            callback: function (r) {

                if (!r.message || r.message.length === 0) {
                    frappe.msgprint("No breakup rows found.");
                    return;
                }

                let dialog = new frappe.ui.Dialog({
                    title: "Breakup Details",
                    size: "extra-large",
                    fields: [
                        {
                            fieldname: "breakup_table",
                            fieldtype: "Table",
                            label: "Breakup",
                            read_only: 1,
                            cannot_add_rows: true,
                            data: r.message,
                            fields: [
                                { fieldname: "attribute_type", label: "Attribute Type", fieldtype: "Data", in_list_view: 1 },
                                { fieldname: "attribute_value", label: "Attribute Value", fieldtype: "Data", in_list_view: 1 },
                                { fieldname: "weight", label: "Weight", fieldtype: "Float", in_list_view: 1 },
                                { fieldname: "price", label: "Price", fieldtype: "Float", in_list_view: 1 },
                                { fieldname: "unit", label: "Unit", fieldtype: "Data", in_list_view: 1 }
                            ]
                        }
                    ]
                });

                dialog.show();
            }
        });
    }
});