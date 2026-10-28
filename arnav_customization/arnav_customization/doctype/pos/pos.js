
function is_pos(frm) {
    return frm.doc.doctype === "POS";
}

/* =====================================================
POS MAIN FORM
===================================================== */

frappe.ui.form.on('POS', {

    setup: function (frm) {

        console.log("POS SETUP");

        // =========================================
        // PRODUCT FILTER
        // =========================================

        frm.set_query("product", "sku_details", function (doc) {

            if (!doc.billtype) {

                return {
                    filters: {
                        name: ""
                    }
                };
            }

            return {
                filters: {
                    custom_metal: doc.billtype
                }
            };
        });

        // =========================================
        // CREDIT NOTE FILTER
        // =========================================

        frm.set_query("credit_note", "payment_details", function (doc) {

            return {
                filters: {
                    customer: doc.client_name || ""
                }
            };
        });
        
        // =========================================
        // PAYMENT ENTRY FILTER - ALL PAYMENT TYPES
        // =========================================
        frm.set_query(
            "custom_payment_entry",
            "payment_details",
            function (doc) {

                if (!doc.client_name) {
                    return {
                        filters: {
                            name: ["=", ""]
                        }
                    };
                }

                return {
                    query: "arnav_customization.advance_payment.get_eligible_payment_entries",
                    filters: {
                        customer: doc.client_name,
                        company: frappe.defaults.get_user_default("Company")
                    }
                };
            }
        );
        // =========================================
        // PACKING MATERIAL FILTER
        // =========================================

        frm.set_query("packing_material", "packing_materials", function () {

            return {
                filters: {
                    item_group: "PACKING METERIALS"
                }
            };
        });
    },

    // =========================================
    // ONLOAD
    // =========================================

    onload: function (frm) {

        console.log("POS ONLOAD");

        console.log("CLIENT BEFORE:", frm.doc.client_name);

        // =========================================
        // AUTO FETCH USER BRANCH
        // =========================================

        if (frm.is_new() && !frm.doc.branch) {

            frappe.call({
                method: "frappe.client.get_value",
                args: {
                    doctype: "User",
                    filters: {
                        name: frappe.session.user
                    },
                    fieldname: ["branch"]
                },
                callback: function (r) {

                    if (!frm.is_new() || frm.doc.branch) {
                        return;
                    }

                    if (r.message && r.message.branch) {

                        frm.set_value(
                            "branch",
                            r.message.branch
                        );

                        frm.set_df_property(
                            "branch",
                            "read_only",
                            1
                        );

                        console.log(
                            "USER BRANCH:",
                            r.message.branch
                        );
                    }
                }
            });
        }

        console.log("CLIENT AFTER:", frm.doc.client_name);
    },

    // =========================================
    // REFRESH
    // =========================================

    // refresh: function (frm) {

    //     console.log("POS REFRESH:", frm.doc.client_name);

    //     if (frm.is_new()) {
    //         return;
    //     }

    //     if (frm.doc.docstatus === 1) {

    //         frm.add_custom_button(__('Sales Return'), function () {

    //             frappe.model.open_mapped_doc({
    //                 method: "arnav_customization.arnav_customization.doctype.pos.pos.make_credit_note",
    //                 frm: frm
    //             });

    //         }, __("Create"));

    //         return;
    //     }

    //     // Do not recalculate on refresh for saved draft docs.
    //     // Recalculation here makes the form dirty again after Save.
    // },

    
    // =========================================
    // REFRESH
    // =========================================

    refresh: function (frm) {

        console.log("POS REFRESH:", frm.doc.client_name);

        if (frm.is_new()) {
            return;
        }

        if (frm.doc.docstatus === 1) {

            // Existing Sales Return option
            frm.add_custom_button(__('Sales Return'), function () {

                frappe.model.open_mapped_doc({
                    method: "arnav_customization.arnav_customization.doctype.pos.pos.make_credit_note",
                    frm: frm
                });

            }, __("Create"));

            // NEW: Create Sales Invoice option
            frm.add_custom_button(__('Create Sales Invoice'), function () {

                frappe.model.open_mapped_doc({
                    method: "arnav_customization.arnav_customization.doctype.pos.pos.make_sales_invoice",
                    frm: frm
                });

            }, __("Create"));

            return;
        }

        // Do not recalculate on refresh for saved draft docs.
        // Recalculation here makes the form dirty again after Save.
    },

    // =========================================
    // VALIDATE
    // =========================================

    validate: function (frm) {

        console.log("VALIDATE CLIENT:", frm.doc.client_name);
    },

    // =========================================
    // BEFORE SUBMIT
    // =========================================

    before_submit: function (frm) {

        let balance = flt(frm.doc.balance_amount);

        if (Math.abs(balance) > 0.01) {

            frappe.throw({
                title: __("Submission Not Allowed"),
                message: __(
                    "Cannot submit POS because Balance Amount must be 0.00. Current Balance: "
                ) + balance
            });
        }
    },

    handling_and_packaging_charges: function (frm) {
        calculate_parent_totals(frm);
    },

    custom_huid_charges: function (frm) {
        calculate_parent_totals(frm);
    },

    total_discount_in_rs: function (frm) {
        apply_global_discount(frm);
    }

});

/* =====================================================
SKU TABLE
===================================================== */

frappe.ui.form.on('POS SKU Details', {

    price: function (frm) {
        apply_global_discount(frm);
    },

    qty: function (frm) {
        apply_global_discount(frm);
    },

    gst_percentage: function (frm) {
        apply_global_discount(frm);
    },

    sku_details_add: function (frm) {
        setTimeout(() => {
            apply_global_discount(frm);
        }, 200);
    },

    sku_details_remove: function (frm) {
        calculate_parent_totals(frm);
    },

    /* =================================================
    ONLY FIRST ROW DISCOUNT ENTRY
    converts to %
    then applies same % to all rows
    ================================================= */
    discount: function (frm, cdt, cdn) {

        let row = locals[cdt][cdn];
        let rows = frm.doc.sku_details || [];

        if (!rows.length) return;

        let first_row = rows[0];

        if (row.name === first_row.name) {

            let amount = flt(first_row.price) * flt(first_row.qty);
            let disc = flt(first_row.discount);

            let perc = 0;

            if (amount > 0) {
                perc = (disc / amount) * 100;
            }

            frm.set_value("discount_percentage", perc);

            apply_global_discount(frm);

        } else {

            apply_global_discount(frm);
        }
    },

    sku: function (frm, cdt, cdn) {

        let row = locals[cdt][cdn];
        if (!row.sku) return;

        frappe.db.get_value("SKU", row.sku,
            ["product", "gross_weight", "net_weight", "batch_no"]
        ).then(r => {

            if (!r.message) {
                frappe.throw(__("The selected SKU no longer exists."));
            }

            let item = r.message.product;

            if (!r.message.batch_no) {
                frappe.throw(__("The selected SKU has no linked Batch. Please contact an administrator."));
            }

            frappe.model.set_value(cdt, cdn, "product", item);
            frappe.model.set_value(cdt, cdn, "batch_no", r.message.batch_no);
            frappe.model.set_value(cdt, cdn, "gross_weight", r.message.gross_weight);
            frappe.model.set_value(cdt, cdn, "net_weight", r.message.net_weight);

            return frappe.db.get_doc("Item", item);

        }).then(item_doc => {

            if (!item_doc) return;

            if (item_doc.gst_hsn_code) {
                frappe.model.set_value(cdt, cdn, "hsn", item_doc.gst_hsn_code);
            }

            if (item_doc.taxes && item_doc.taxes.length) {

                let template = item_doc.taxes[0].item_tax_template;

                if (template) {
                    return frappe.db.get_value(
                        "Item Tax Template",
                        template,
                        "gst_rate"
                    );
                }
            }

        }).then(r => {

            if (r && r.message && r.message.gst_rate) {
                frappe.model.set_value(cdt, cdn, "gst_percentage", r.message.gst_rate);
            } else {
                frappe.model.set_value(cdt, cdn, "gst_percentage", 0);
            }

            apply_global_discount(frm);
        }).catch(error => {
            frappe.model.set_value(cdt, cdn, "product", "");
            frappe.model.set_value(cdt, cdn, "batch_no", "");
            frappe.msgprint({
                title: __("SKU Lookup Failed"),
                indicator: "red",
                message: error && error.message
                    ? error.message
                    : __("Unable to load SKU details. Please select the SKU again.")
            });
        });
    }

});

/* =====================================================
HELPERS
===================================================== */

function same_number(a, b, precision = 6) {
    return Number(flt(a).toFixed(precision)) === Number(flt(b).toFixed(precision));
}

function set_parent_if_changed(frm, fieldname, value, precision = 6) {
    if (!same_number(frm.doc[fieldname], value, precision)) {
        frm.set_value(fieldname, value);
    }
}

function set_child_if_changed(row, fieldname, value, precision = 6) {
    if (!same_number(row[fieldname], value, precision)) {
        frappe.model.set_value(row.doctype, row.name, fieldname, value);
    }
}

/* =====================================================
APPLY SAME % TO ALL ROWS
===================================================== */

function apply_global_discount(frm) {

    if (is_submitted_pos(frm)) {
        return;
    }

    let rows = frm.doc.sku_details || [];
    let total_price = 0;

    rows.forEach(r => {
        total_price += flt(r.price) * flt(r.qty);
    });

    let total_discount = flt(frm.doc.total_discount_in_rs);
    let perc = 0;

    if (total_price > 0) {
        perc = (total_discount / total_price) * 100;
    }

    set_parent_if_changed(frm, "total_price", money(total_price), 2);
    set_parent_if_changed(frm, "discount_percentage", perc, 6);

    rows.forEach(r => {

        let amount = flt(r.price) * flt(r.qty);
        let disc = money((amount * perc) / 100);

        let final_amount = money(amount - disc);

        if (final_amount < 0) {
            final_amount = 0;
        }

        let gst_amount = money((final_amount * flt(r.gst_percentage)) / 100);

        set_child_if_changed(r, "discount", disc, 2);
        set_child_if_changed(r, "final_amount", final_amount, 2);
        set_child_if_changed(r, "gst_amount", gst_amount, 2);
    });

    calculate_parent_totals(frm);
}

/* =====================================================
TOTALS
===================================================== */

function calculate_parent_totals(frm) {

    if (is_submitted_pos(frm)) {
        return;
    }

    let total_amount = 0;
    let total_gst = 0;

    (frm.doc.sku_details || []).forEach(row => {

        total_amount += flt(row.final_amount);
        total_gst += flt(row.gst_amount);

    });

    let packing = flt(frm.doc.handling_and_packaging_charges);
    let huidCharges = flt(frm.doc.custom_huid_charges);

    set_parent_if_changed(
        frm,
        "total_amount_wo_tax",
        money(total_amount + packing + huidCharges),
        2
    );

    set_parent_if_changed(
        frm,
        "total_amount_with_gst",
        money(total_amount + total_gst + packing),
        2
    );

    calculate_balance(frm);
}

/* =====================================================
PAYMENT
===================================================== */

// frappe.ui.form.on('POS Payment Details', {

//     amount: function (frm) {
//         calculate_payments(frm);
//     },

//     payment_details_remove: function (frm) {
//         calculate_payments(frm);
//     }

// });

// function calculate_payments(frm) {

//     if (is_submitted_pos(frm)) {
//         return;
//     }

//     let paid = 0;

//     (frm.doc.payment_details || []).forEach(row => {
//         paid += flt(row.amount);
//     });

//     set_parent_if_changed(frm, "paid_amount", money(paid), 2);

//     calculate_balance(frm);
// }


frappe.ui.form.on('POS Payment Details', {

    custom_payment_entry: async function (frm, cdt, cdn) {
        const row = locals[cdt][cdn];

        if (!row.custom_payment_entry) {
            await frappe.model.set_value(cdt, cdn, "amount", 0);
            return;
        }

        try {
            const response = await frappe.call({
                method: "arnav_customization.advance_payment.fetch_advance_amount",
                args: {
                    payment_entry: row.custom_payment_entry
                }
            });

            // Ignore the response if the selected Payment Entry changed
            if (
                !locals[cdt][cdn] ||
                locals[cdt][cdn].custom_payment_entry !== row.custom_payment_entry
            ) {
                return;
            }

            if (response.message) {
                const payment_amount = flt(
                    response.message.payment_amount
                );

                await frappe.model.set_value(
                    cdt,
                    cdn,
                    "amount",
                    money(payment_amount)
                );
            } else {
                frappe.msgprint(
                    __("Could not fetch the amount for this Payment Entry.")
                );
            }

        } catch (error) {
            frappe.msgprint(
                __("Error fetching Payment Entry amount. Please check the server method.")
            );
            console.error(error);
        }
    },

    amount: function (frm) {
        calculate_payments(frm);
    },

    payment_details_remove: function (frm) {
        calculate_payments(frm);
    }

});

/* =====================================================
BALANCE
===================================================== */

function calculate_balance(frm) {

    if (is_submitted_pos(frm)) {
        return;
    }

    let total = flt(frm.doc.total_amount_with_gst);
    let paid = flt(frm.doc.paid_amount);

    set_parent_if_changed(frm, "balance_amount", money(total - paid), 2);
}

/* =====================================================
LOAD
===================================================== */

function calculate_all(frm) {

    if (is_submitted_pos(frm)) {
        return;
    }

    apply_global_discount(frm);
    calculate_payments(frm);
}

/* =====================================================
SAFE FLOAT
===================================================== */

function flt(val) {
    return parseFloat(val) || 0;
}

function money(val) {
    return Math.round((flt(val) + Number.EPSILON) * 100) / 100;
}

function is_submitted_pos(frm) {
    return is_pos(frm) && frm.doc.docstatus === 1;
}
