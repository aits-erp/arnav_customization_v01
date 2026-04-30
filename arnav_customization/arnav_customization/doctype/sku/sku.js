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

    // ✅ generate breakup_ref if missing editable field to link breakup rows to this SKU
    if (!frm.doc.breakup_ref) {
        frm.set_value("breakup_ref", frappe.utils.get_random(12));
    }

    frappe.call({
        method: "arnav_customization.arnav_customization.doctype.sku_master.sku_master.get_breakup_rows",
        args: {
            sku_master: frm.doc.sku_master,
            breakup_ref: frm.doc.breakup_ref
        },
        callback: function (r) {

            let dynamic_fields = [
                {
                    fieldname: "attribute_type",
                    label: "Attribute Type",
                    fieldtype: "Select",
                    options: `PRODUCT_TYPE
                        PURITY
                        STONE
                        COLLECTION
                        DESIGN
                        VISUAL
                        USAGE
                        TARGET`,
                    in_list_view: 1
                },
                {
                    fieldname: "attribute_value",
                    label: "Attribute Value",
                    fieldtype: "Link",
                    options: "",
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
                    fieldtype: "Select",
                    options: "\nGram\nCarat",
                    in_list_view: 1
                }
            ];

            let dialog = new frappe.ui.Dialog({
                title: "Manage Breakup",
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
                            sku_master: frm.doc.sku_master,
                            breakup_ref: frm.doc.breakup_ref,
                            rows: JSON.stringify(values.breakup_table || [])
                        },
                        callback() {
                            frappe.msgprint("Breakup updated successfully");
                            dialog.hide();
                            frm.reload_doc();
                        }
                    });
                }
            });

            dialog.show();

            // 🔥 same dynamic link logic as SKU Master
            let grid = dialog.fields_dict.breakup_table.grid;

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

});