frappe.ui.form.on("Stock Entry Detail", {

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

                // UI display qty as gross weight
                frappe.model.set_value(cdt, cdn, "qty", d.gross_weight);

                // preserve separately
                frappe.model.set_value(cdt, cdn, "custom_gross_weight", d.gross_weight);

                frappe.model.set_value(cdt, cdn, "batch_no", d.batch_no);

                setTimeout(() => {

                    frappe.model.set_value(cdt, cdn, "basic_rate", d.cost_price);

                    frappe.model.set_value(cdt, cdn, "valuation_rate", d.valuation_rate);

                }, 300);

                if (!row.s_warehouse && !row.t_warehouse) {

                    frappe.model.set_value(cdt, cdn, "t_warehouse", d.warehouse);
                }
            }
        });
    }
});


frappe.ui.form.on("Stock Entry", {

    refresh(frm) {

        // enable only for transfer / issue
        if (
            frm.doc.purpose === "Material Transfer" ||
            frm.doc.purpose === "Material Issue"
        ) {

            frm.set_value("custom_use_qty_mode", 1);

        } else {

            frm.set_value("custom_use_qty_mode", 0);
        }
    }
});
