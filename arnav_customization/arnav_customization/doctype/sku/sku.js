const design_code_method_base = "arnav_customization.arnav_customization.doctype.sku_master.sku_master";

frappe.ui.form.on("SKU", {
    refresh(frm) {
        frm.set_df_property("breakup_info", "label", frm.doc.breakup_ref ? "Edit Breakup" : "Add Breakup");
    },

    async breakup_info(frm) {
        if (!frm.doc.breakup_ref) {
            await frm.set_value("breakup_ref", frappe.utils.get_random(12));
        }

        if (frm.is_dirty()) {
            await frm.save();
        }

        frappe.call({
            method: `${design_code_method_base}.get_breakup_rows`,
            args: { sku_master: frm.doc.sku_master, breakup_ref: frm.doc.breakup_ref },
            callback: (breakup_response) => {
                frappe.call({
                    method: `${design_code_method_base}.get_breakup_design_state`,
                    args: { sku_master: frm.doc.sku_master, breakup_ref: frm.doc.breakup_ref },
                    callback: (state_response) => {
                        const dialog = create_sku_design_breakup_dialog(
                            frm,
                            breakup_response.message || [],
                            state_response.message || {}
                        );
                        dialog.show();
                    }
                });
            }
        });
    }
});

function create_sku_design_breakup_dialog(frm, breakup_rows, state) {
    const locked = Boolean(state.classification_locked);
    const fields = [
        {
            fieldname: "attribute_type",
            label: "Attribute Type",
            fieldtype: "Select",
            options: "\nELEMENT_CODE\nPURITY\nSTONE\nSET_CODE\nDESIGN\nVISUAL\nUSAGE\nTARGET",
            in_list_view: 1
        },
        { fieldname: "attribute_value", label: "Attribute Value", fieldtype: "Link", options: "", in_list_view: 1 },
        { fieldname: "weight", label: "Weight", fieldtype: "Float", in_list_view: 1 },
        { fieldname: "price", label: "Price", fieldtype: "Float", in_list_view: 1 },
        { fieldname: "unit", label: "Unit", fieldtype: "Select", options: "\nGram\nCarat", in_list_view: 1 }
    ];
    const dialog = new frappe.ui.Dialog({
        title: __("Manage Breakup"),
        size: "extra-large",
        fields: [
            {
                fieldname: "design_code_display",
                label: __("Design Code"),
                fieldtype: "Data",
                read_only: 1,
                default: state.design_code || __("Not generated")
            },
            {
                fieldname: "existing_design_code",
                label: __("Use Existing Design Code"),
                fieldtype: "Link",
                options: "Design Code",
                hidden: locked,
                get_query: () => ({
                    filters: { status: "Active", set_code: state.set_code || "", element_code: state.element_code || "" }
                })
            },
            { fieldname: "assign_existing", label: __("Assign Existing Design Code"), fieldtype: "Button", hidden: locked },
            {
                fieldname: "breakup_table",
                fieldtype: "Table",
                label: __("Breakup Details"),
                in_place_edit: true,
                cannot_add_rows: false,
                data: breakup_rows,
                get_data: () => breakup_rows,
                fields
            }
        ]
    });

    const finish = (saved_breakup) => {
        if (saved_breakup.breakup_ref && saved_breakup.breakup_ref !== frm.doc.breakup_ref) {
            frm.set_value("breakup_ref", saved_breakup.breakup_ref);
        }
        dialog.hide();
        frm.reload_doc();
    };
    const save_breakup = (after_save) => {
        const values = dialog.get_values() || {};
        frappe.call({
            method: `${design_code_method_base}.save_breakup_rows`,
            args: {
                sku_master: frm.doc.sku_master,
                breakup_ref: frm.doc.breakup_ref,
                rows: JSON.stringify(values.breakup_table || [])
            },
            callback: (response) => after_save(response.message || {})
        });
    };

    dialog.set_primary_action(__("Save Breakup"), () => {
        save_breakup((saved_breakup) => {
            frappe.show_alert({ message: __("Breakup saved"), indicator: "green" });
            finish(saved_breakup);
        });
    });

    dialog.set_secondary_action(locked ? __("Correct Classification") : __("Generate Design Code"), () => {
        if (locked) {
            frappe.prompt(
                [{ fieldname: "reason", label: __("Correction reason"), fieldtype: "Small Text", reqd: 1 }],
                (values) => frappe.call({
                    method: `${design_code_method_base}.release_design_code_assignment`,
                    args: { sku_master: frm.doc.sku_master, breakup_ref: frm.doc.breakup_ref, reason: values.reason },
                    callback: () => finish({ breakup_ref: frm.doc.breakup_ref })
                }),
                __("Correct Design Classification"),
                __("Unlock")
            );
            return;
        }

        frappe.confirm(
            __("This will save the breakup, generate a permanent Design Code, and lock Set Code and Element Code. Continue?"),
            () => save_breakup((saved_breakup) => frappe.call({
                method: `${design_code_method_base}.generate_design_code`,
                args: { sku_master: frm.doc.sku_master, breakup_ref: saved_breakup.breakup_ref },
                callback: (response) => {
                    frappe.msgprint({
                        title: __("Design Code Assigned"),
                        message: __("Design Code {0} is now fixed.", [(response.message || {}).design_code]),
                        indicator: "green"
                    });
                    finish(saved_breakup);
                }
            }))
        );
    });

    const original_show = dialog.show;
    dialog.show = function () {
        original_show.call(dialog);
        const grid = dialog.fields_dict.breakup_table.grid;
        grid.wrapper.on("focus", "input[data-fieldname='attribute_value']", function () {
            const grid_row = $(this).closest(".grid-row").data("grid_row");
            if (grid_row && grid_row.doc.attribute_type) {
                grid.update_docfield_property("attribute_value", "options", grid_row.doc.attribute_type);
            }
        });

        if (locked) {
            (grid.grid_rows || []).forEach((grid_row) => {
                if (["SET_CODE", "ELEMENT_CODE"].includes(grid_row.doc.attribute_type)) {
                    grid_row.toggle_editable("attribute_type", false);
                    grid_row.toggle_editable("attribute_value", false);
                }
            });
        } else {
            dialog.fields_dict.assign_existing.$input.on("click", () => {
                const design_code = dialog.get_value("existing_design_code");
                if (!design_code) {
                    frappe.msgprint(__("Select an existing Design Code first."));
                    return;
                }
                save_breakup((saved_breakup) => frappe.call({
                    method: `${design_code_method_base}.assign_existing_design_code`,
                    args: { sku_master: frm.doc.sku_master, breakup_ref: saved_breakup.breakup_ref, design_code },
                    callback: () => finish(saved_breakup)
                }));
            });
        }
    };

    return dialog;
}
