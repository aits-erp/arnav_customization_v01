frappe.ui.form.on("Quotation Item", {

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

                frappe.model.set_value(cdt, cdn, "warehouse", d.warehouse);

            }
        });

    }

});