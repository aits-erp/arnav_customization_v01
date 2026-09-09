frappe.provide("arnav_customization.design_code");

(() => {
    const method_base = "arnav_customization.arnav_customization.doctype.sku_master.sku_master";
    const classification_types = ["SET_CODE", "ELEMENT_CODE"];
    const manual_attribute_types = ["DESIGN_CODE"];
    const locked_attribute_types = [...classification_types, ...manual_attribute_types];

    const breakup_fields = [
        {
            fieldname: "attribute_type",
            label: __("Attribute Type"),
            fieldtype: "Select",
            options: "\nELEMENT_CODE\nPURITY\nSTONE\nSET_CODE\nDESIGN\nVISUAL\nDESIGN_CODE\nTARGET",
            in_list_view: 1
        },
        {
            fieldname: "attribute_value",
            label: __("Attribute Value"),
            fieldtype: "Data",
            options: "",
            in_list_view: 1
        },
        { fieldname: "weight", label: __("Weight"), fieldtype: "Float", in_list_view: 1 },
        { fieldname: "price", label: __("Price"), fieldtype: "Float", in_list_view: 1 },
        { fieldname: "unit", label: __("Unit"), fieldtype: "Select", options: "\nGram\nCarat", in_list_view: 1 }
    ];

    function get_breakup_rows(dialog) {
        return dialog.fields_dict.breakup_table.grid.get_data() || [];
    }

    function has_complete_classification(dialog) {
        const rows = get_breakup_rows(dialog);
        return classification_types.every((attribute_type) => (
            rows.filter((row) => row.attribute_type === attribute_type && row.attribute_value).length === 1
        ));
    }

    function set_button_enabled(dialog, fieldname, enabled) {
        const field = dialog.fields_dict[fieldname];
        if (field && field.$input) {
            field.$input.prop("disabled", !enabled);
        }
    }

    function lock_classification_rows(dialog) {
        const grid = dialog.fields_dict.breakup_table.grid;
        (grid.grid_rows || []).forEach((grid_row) => {
            if (locked_attribute_types.includes(grid_row.doc.attribute_type)) {
                grid_row.toggle_editable("attribute_type", false);
                grid_row.toggle_editable("attribute_value", false);
            }
        });
    }

    function get_manual_design_code(dialog) {
        const values = get_breakup_rows(dialog)
            .filter((row) => row.attribute_type === "DESIGN_CODE" && row.attribute_value)
            .map((row) => String(row.attribute_value).trim().toUpperCase());
        return values.length === 1 ? values[0] : null;
    }

    function configure_attribute_value_control(grid, grid_row) {
        if (!grid_row) return;

        const attribute_type = grid_row.doc.attribute_type;
        const is_manual = manual_attribute_types.includes(attribute_type);

        grid.update_docfield_property(
            "attribute_value",
            "fieldtype",
            is_manual ? "Data" : "Link"
        );
        grid.update_docfield_property(
            "attribute_value",
            "options",
            is_manual ? "" : attribute_type
        );
        grid.update_docfield_property(
            "attribute_value",
            "description",
            is_manual
                ? __("Enter the Design Code exactly as supplied by the client.")
                : ""
        );
        grid_row.refresh_field("attribute_value");
    }

    function save_breakup(dialog, options, after_save) {
        const values = dialog.get_values() || {};
        frappe.call({
            method: `${method_base}.save_breakup_rows`,
            args: {
                sku_master: options.sku_master,
                breakup_ref: options.breakup_ref,
                rows: JSON.stringify(values.breakup_table || [])
            },
            callback: (response) => after_save(response.message || {})
        });
    }

    function create_dialog(options, breakup_rows, state) {
        const locked = Boolean(state.classification_locked);
        const dialog = new frappe.ui.Dialog({
            title: options.title,
            size: "extra-large",
            fields: [
                {
                    fieldname: "design_code",
                    label: __("Design Code"),
                    fieldtype: "Link",
                    options: "Design Code",
                    read_only: 1,
                    default: state.design_code || ""
                },
                {
                    fieldname: "design_code_status",
                    fieldtype: "HTML",
                    options: state.design_code
                        ? `<div class="text-muted">${__("{0} Design Code is assigned and classification is locked.", [state.generation_mode || ""] )}</div>`
                        : state.manual_design_code
                            ? `<div class="text-muted">${__("Manual Design Code {0} will be created or assigned when you select Generate Design Code.", [state.manual_design_code])}</div>`
                            : `<div class="text-muted">${__("No manual code entered. Generate Design Code will use the next automatic series.")}</div>`
                },
                {
                    fieldname: "generate_design_code",
                    label: __("Generate Design Code"),
                    fieldtype: "Button",
                    hidden: locked
                },
                {
                    fieldname: "existing_design_code",
                    label: __("Use Existing Design Code"),
                    fieldtype: "Link",
                    options: "Design Code",
                    hidden: locked,
                    get_query: () => ({
                        filters: {
                            status: "Active",
                            set_code: state.set_code || "",
                            element_code: state.element_code || ""
                        }
                    })
                },
                {
                    fieldname: "assign_existing_design_code",
                    label: __("Assign Existing Design Code"),
                    fieldtype: "Button",
                    hidden: locked
                },
                {
                    fieldname: "correct_design_classification",
                    label: __("Replace Design Code"),
                    fieldtype: "Button",
                    hidden: !locked
                },
                {
                    fieldname: "breakup_table",
                    fieldtype: "Table",
                    label: __("Breakup Details"),
                    in_place_edit: true,
                    cannot_add_rows: false,
                    data: breakup_rows,
                    get_data: () => breakup_rows,
                    fields: breakup_fields
                }
            ],
            primary_action_label: __("Save Breakup"),
            primary_action() {
                save_breakup(dialog, options, (saved_breakup) => {
                    frappe.show_alert({ message: __("Breakup saved"), indicator: "green" });
                    options.on_saved(saved_breakup);
                });
            }
        });

        const finish = (saved_breakup) => {
            options.on_saved(saved_breakup);
            dialog.hide();
        };

        dialog.on_page_show = () => {
            const grid = dialog.fields_dict.breakup_table.grid;
            grid.wrapper.on("change", "select[data-fieldname='attribute_type']", function () {
                const grid_row = $(this).closest(".grid-row").data("grid_row");
                setTimeout(() => configure_attribute_value_control(grid, grid_row), 0);
            });
            grid.wrapper.on("focus", "input[data-fieldname='attribute_value']", function () {
                const grid_row = $(this).closest(".grid-row").data("grid_row");
                if (grid_row && grid_row.doc.attribute_type) {
                    configure_attribute_value_control(grid, grid_row);
                }
            });

            const refresh_generate_button = () => {
                set_button_enabled(dialog, "generate_design_code", !locked && has_complete_classification(dialog));
                const manual_design_code = get_manual_design_code(dialog);
                const button = dialog.fields_dict.generate_design_code;
                if (button && button.$input) {
                    button.$input.text(manual_design_code
                        ? __("Create Manual Design Code")
                        : __("Generate Auto Design Code"));
                }
            };
            grid.wrapper.on("change", "input, select", () => setTimeout(refresh_generate_button, 0));
            refresh_generate_button();

            if (locked) {
                lock_classification_rows(dialog);
            }

            if (!locked) {
                dialog.fields_dict.generate_design_code.$input.on("click", () => {
                    if (!has_complete_classification(dialog)) {
                        frappe.msgprint(__("Add exactly one Set Code and one Element Code before generating a Design Code."));
                        return;
                    }

                    frappe.confirm(
                        get_manual_design_code(dialog)
                            ? __("This will save the breakup, create or assign the manual Design Code, and lock it permanently. Continue?")
                            : __("This will save the breakup, generate the next permanent Design Code, and lock Set Code and Element Code. Continue?"),
                        () => save_breakup(dialog, options, (saved_breakup) => {
                            frappe.call({
                                method: `${method_base}.generate_design_code`,
                                args: { sku_master: options.sku_master, breakup_ref: saved_breakup.breakup_ref },
                                callback: (response) => {
                                    const result = response.message || {};
                                    frappe.msgprint({
                                        title: __("Design Code Assigned"),
                                        message: __("{0} Design Code {1} is now fixed.", [result.generation_mode || "", result.design_code]),
                                        indicator: "green"
                                    });
                                    finish(saved_breakup);
                                }
                            });
                        })
                    );
                });

                dialog.fields_dict.assign_existing_design_code.$input.on("click", () => {
                    const design_code = dialog.get_value("existing_design_code");
                    if (!design_code) {
                        frappe.msgprint(__("Select an existing Design Code first."));
                        return;
                    }

                    save_breakup(dialog, options, (saved_breakup) => {
                        frappe.call({
                            method: `${method_base}.assign_existing_design_code`,
                            args: {
                                sku_master: options.sku_master,
                                breakup_ref: saved_breakup.breakup_ref,
                                design_code
                            },
                            callback: () => finish(saved_breakup)
                        });
                    });
                });
            } else {
                dialog.fields_dict.correct_design_classification.$input.on("click", () => {
                    frappe.prompt(
                        [{ fieldname: "reason", label: __("Correction reason"), fieldtype: "Small Text", reqd: 1 }],
                        (values) => frappe.call({
                            method: `${method_base}.release_design_code_assignment`,
                            args: {
                                sku_master: options.sku_master,
                                breakup_ref: options.breakup_ref,
                                reason: values.reason
                            },
                            callback: () => finish({ breakup_ref: options.breakup_ref })
                        }),
                        __("Replace Design Code"),
                        __("Replace")
                    );
                });
            }
        };

        const original_show = dialog.show;
        dialog.show = function () {
            original_show.call(dialog);
            dialog.on_page_show();
        };

        return dialog;
    }

    arnav_customization.design_code.open_breakup_dialog = (options) => {
        frappe.call({
            method: `${method_base}.get_breakup_rows`,
            args: { sku_master: options.sku_master, breakup_ref: options.breakup_ref },
            callback: (breakup_response) => {
                frappe.call({
                    method: `${method_base}.get_breakup_design_state`,
                    args: { sku_master: options.sku_master, breakup_ref: options.breakup_ref },
                    callback: (state_response) => {
                        create_dialog(options, breakup_response.message || [], state_response.message || {}).show();
                    }
                });
            }
        });
    };
})();
