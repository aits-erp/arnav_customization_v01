frappe.ui.form.on('Sales Invoice', {
    refresh(frm) {

        const fields_to_hide = [
            "custom_custom_fields",
            "custom_weight",
            "custom_purity",
            "custom_custom_rate"
        ];

        if (frm.fields_dict.items && frm.fields_dict.items.grid) {
            fields_to_hide.forEach(field => {
                frm.fields_dict.items.grid.update_docfield_property(
                    field,
                    "hidden",
                    1
                );
            });

            frm.refresh_field("items");
        }
    }
});
