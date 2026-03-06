frappe.ui.form.on("Stock Entry Detail", {

    custom_sku: function(frm, cdt, cdn) {

        let row = locals[cdt][cdn];

        if (!row.custom_sku) return;

        frappe.call({
            method: "arnav_customization.sku_mapping_backend.sku_mapper.get_sku_data",
            args: { sku: row.custom_sku },

            callback: function(r) {

                if (!r.message) return;

                let d = r.message;

                frappe.model.set_value(cdt, cdn, "item_code", d.item_code);

                // client rule
                frappe.model.set_value(cdt, cdn, "qty", d.gross_weight);

                // IMPORTANT
                frappe.model.set_value(cdt, cdn, "batch_no", d.batch_no);

                // prevents popup
                frappe.model.set_value(cdt, cdn, "use_serial_batch_fields", 1);

                frappe.model.set_value(cdt, cdn, "basic_rate", d.rate);

                frappe.model.set_value(cdt, cdn, "valuation_rate", d.valuation_rate);

                if (!row.s_warehouse && !row.t_warehouse) {
                    frappe.model.set_value(cdt, cdn, "t_warehouse", d.warehouse);
                }

            }
        });

    }

});