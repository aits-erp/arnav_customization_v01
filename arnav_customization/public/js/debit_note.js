function calculate_debit_note_rate(frm, cdt, cdn) {

    let row = locals[cdt][cdn];

    if (!row.custom_sku || !row.qty) return;

    let gross_weight = flt(row.qty);

    if (gross_weight <= 0) return;

    // Fetch cost_price from SKU
    frappe.db.get_value("SKU", row.custom_sku, "cost_price")
        .then(r => {
            if (r.message && r.message.cost_price) {

                let cost_price = flt(r.message.cost_price);

                let rate = cost_price / gross_weight;

                setTimeout(() => {
                    frappe.model.set_value(cdt, cdn, "rate", d.rate);
                }, 300);
            }
        });
}

frappe.ui.form.on('Purchase Invoice Item', {
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
                
                frappe.model.set_value(cdt, cdn, "gst_hsn_code", d.hsn);

                frappe.model.set_value(cdt, cdn, "warehouse", d.warehouse);

                frappe.model.set_value(cdt, cdn, "batch_no", d.batch_no);

                // prevents batch popup
                frappe.model.set_value(cdt, cdn, "use_serial_batch_fields", 1);

                // calculate rate
                calculate_debit_note_rate(frm, cdt, cdn);

            }
        });
    },

    qty: function(frm, cdt, cdn) {
        calculate_debit_note_rate(frm, cdt, cdn);
    },

    custom_quantity: function(frm, cdt, cdn) {
        calculate_debit_note_rate(frm, cdt, cdn);
    }

});

