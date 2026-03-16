frappe.ui.form.on('Credit Note', {

    refresh(frm) {

        const fields_to_show = [
            "custom_custom_fields",
            "custom_weight",
            "custom_purity",
            "custom_custom_rate"
        ];

        if (frm.fields_dict.items && frm.fields_dict.items.grid) {
            fields_to_show.forEach(field => {
                frm.fields_dict.items.grid.update_docfield_property(
                    field,
                    "hidden",
                    0
                );
            });

            frm.refresh_field("items");
        }
    }
});


frappe.ui.form.on('Sales Invoice Item', {

    custom_weight(frm, cdt, cdn) {
        calculate_custom_rate(frm, cdt, cdn);
    },

    custom_custom_rate(frm, cdt, cdn) {
        calculate_custom_rate(frm, cdt, cdn);
    },

    custom_purity(frm, cdt, cdn) {
        calculate_custom_rate(frm, cdt, cdn);
    }
});


function calculate_custom_rate(frm, cdt, cdn) {

    // Run only inside Credit Note
    if (frm.doctype !== "Credit Note") return;

    let row = locals[cdt][cdn];

    let weight = flt(row.custom_weight);
    let rate = flt(row.custom_custom_rate);
    let purity = flt(row.custom_purity);

    if (weight && rate && purity) {

        let calculated_rate = weight * rate * purity;

        // Set qty = 1 (enforced)
        frappe.model.set_value(cdt, cdn, "qty", 1);

        // Set calculated value into standard rate
        frappe.model.set_value(cdt, cdn, "rate", calculated_rate);

    }
}

frappe.ui.form.on("Sales Invoice Item", {

    custom_sku: function(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!row.custom_sku) return;

        frappe.call({
            method: "arnav_customization.sku_mapping_backend.sku_mapper.get_sku_data",
            args: {
                sku: row.custom_sku
            },

            callback: function(r) {

                if (!r.message) return;

                let d = r.message;

                frappe.model.set_value(cdt, cdn, "item_code", d.item_code);

                frappe.model.set_value(cdt, cdn, "qty", d.gross_weight);

                frappe.model.set_value(cdt, cdn, "custom_net_weight", d.net_weight);

                frappe.model.set_value(cdt, cdn, "custom_quantity", d.qty);

                setTimeout(() => {
                    frappe.model.set_value(cdt, cdn, "rate", d.rate);
                }, 300);
                
                frappe.model.set_value(cdt, cdn, "gst_hsn_code", d.hsn);

                frappe.model.set_value(cdt, cdn, "warehouse", d.warehouse);

                // frappe.model.set_value(cdt, cdn, "batch_no", d.batch_no);

                // prevents batch popup
                // frappe.model.set_value(cdt, cdn, "use_serial_batch_fields", 1);
                
            }
        });

    }

});