// function is_pos(frm) {
//     return frm.doc.doctype === "POS";
// }

// /* =====================================================
// POS MAIN FORM
// ===================================================== */

// frappe.ui.form.on('POS', {

//     setup: function (frm) {

//         console.log("POS SETUP");

//         // =========================================
//         // PRODUCT FILTER
//         // =========================================

//         frm.set_query("product", "sku_details", function (doc) {

//             if (!doc.billtype) {

//                 return {
//                     filters: {
//                         name: ""
//                     }
//                 };
//             }

//             return {
//                 filters: {
//                     custom_metal: doc.billtype
//                 }
//             };
//         });

//         // =========================================
//         // CREDIT NOTE FILTER
//         // =========================================

//         frm.set_query("credit_note", "payment_details", function (doc) {

//             return {
//                 filters: {
//                     customer: doc.client_name || ""
//                 }
//             };
//         });

//         // =========================================
//         // PACKING MATERIAL FILTER
//         // =========================================

//         frm.set_query("packing_material", "packing_materials", function () {

//             return {
//                 filters: {
//                     item_group: "PACKING METERIALS"
//                 }
//             };
//         });
//     },

//     // =========================================
//     // ONLOAD
//     // =========================================

//     onload: function (frm) {

//         console.log("POS ONLOAD");

//         console.log("CLIENT BEFORE:", frm.doc.client_name);

//         // =========================================
//         // AUTO FETCH USER BRANCH
//         // =========================================

//         if (frm.is_new() && !frm.doc.branch) {

//             frappe.call({
//                 method: "frappe.client.get_value",
//                 args: {
//                     doctype: "User",
//                     filters: {
//                         name: frappe.session.user
//                     },
//                     fieldname: ["branch"]
//                 },
//                 callback: function (r) {

//                     if (r.message && r.message.branch) {

//                         frm.set_value(
//                             "branch",
//                             r.message.branch
//                         );

//                         // OPTIONAL:
//                         // make branch readonly

//                         frm.set_df_property(
//                             "branch",
//                             "read_only",
//                             1
//                         );

//                         console.log(
//                             "USER BRANCH:",
//                             r.message.branch
//                         );
//                     }
//                 }
//             });
//         }

//         // IMPORTANT:
//         // preserve route value during initial load

//         if (
//             frm.is_new() &&
//             frappe.route_options &&
//             frappe.route_options.client_name &&
//             !frm.doc.client_name
//         ) {

//             frm.set_value(
//                 "client_name",
//                 frappe.route_options.client_name
//             );
//         }

//         console.log("CLIENT AFTER:", frm.doc.client_name);
//     },

//     onload_post_render: function (frm) {
//         apply_opportunity_client_name(frm);
//     },

//     // =========================================
//     // REFRESH
//     // =========================================

//     refresh: function (frm) {

//         console.log("POS REFRESH:", frm.doc.client_name);

//         // IMPORTANT:
//         // avoid calculations while new doc initializing

//         if (frm.is_new()) {
//             apply_opportunity_client_name(frm);
//             return;
//         }

//         if (!frm.is_new() && frm.doc.docstatus === 1) {

//             frm.add_custom_button(__('Sales Return'), function () {

//                 frappe.model.open_mapped_doc({
//                     method: "arnav_customization.arnav_customization.doctype.pos.pos.make_credit_note",
//                     frm: frm
//                 });

//             }, __("Create"));

//             return;
//         }

//         // calculate_all(frm);
//     if (!frm.is_dirty()) {
//         calculate_all(frm);
// }
//     },

//     // =========================================
//     // VALIDATE
//     // =========================================

//     validate: function (frm) {

//         console.log("VALIDATE CLIENT:", frm.doc.client_name);
//     },

//     // =========================================
//     // BEFORE SUBMIT
//     // =========================================

//     before_submit: function (frm) {

//         let balance = flt(frm.doc.balance_amount);

//         if (Math.abs(balance) > 0.01) {

//             frappe.throw({
//                 title: __("Submission Not Allowed"),
//                 message: __(
//                     "Cannot submit POS because Balance Amount must be 0.00. Current Balance: "
//                 ) + balance
//             });
//         }
//     },

//     handling_and_packaging_charges: function (frm) {
//         calculate_parent_totals(frm);
//     },

//     total_discount_in_rs: function (frm) {
//         apply_global_discount(frm);
//     }

// });

// /* =====================================================
// SKU TABLE
// ===================================================== */

// frappe.ui.form.on('POS SKU Details', {

//     price: function (frm) {
//         apply_global_discount(frm);
//     },

//     qty: function (frm) {
//         apply_global_discount(frm);
//     },

//     gst_percentage: function (frm) {
//         apply_global_discount(frm);
//     },

//     sku_details_add: function (frm) {
//         setTimeout(() => {
//             apply_global_discount(frm);
//         }, 200);
//     },

//     sku_details_remove: function (frm) {
//         calculate_parent_totals(frm);
//     },

//     /* =================================================
//     ONLY FIRST ROW DISCOUNT ENTRY
//     converts to %
//     then applies same % to all rows
//     ================================================= */
//     discount: function (frm, cdt, cdn) {

//         let row = locals[cdt][cdn];
//         let rows = frm.doc.sku_details || [];

//         if (!rows.length) return;

//         let first_row = rows[0];

//         if (row.name === first_row.name) {

//             let amount = flt(first_row.price) * flt(first_row.qty);
//             let disc = flt(first_row.discount);

//             let perc = 0;

//             if (amount > 0) {
//                 perc = (disc / amount) * 100;
//             }

//             frm.set_value("discount_percentage", perc);

//             apply_global_discount(frm);

//         } else {

//             apply_global_discount(frm);
//         }
//     },

//     sku: function (frm, cdt, cdn) {

//         let row = locals[cdt][cdn];
//         if (!row.sku) return;

//         frappe.model.set_value(cdt, cdn, "batch_no", row.sku);

//         frappe.db.get_value("SKU", row.sku,
//             ["product", "gross_weight", "net_weight"]
//         ).then(r => {

//             if (!r.message) return;

//             let item = r.message.product;

//             frappe.model.set_value(cdt, cdn, "product", item);
//             frappe.model.set_value(cdt, cdn, "gross_weight", r.message.gross_weight);
//             frappe.model.set_value(cdt, cdn, "net_weight", r.message.net_weight);

//             return frappe.db.get_doc("Item", item);

//         }).then(item_doc => {

//             if (!item_doc) return;

//             if (item_doc.gst_hsn_code) {
//                 frappe.model.set_value(cdt, cdn, "hsn", item_doc.gst_hsn_code);
//             }

//             if (item_doc.taxes && item_doc.taxes.length) {

//                 let template = item_doc.taxes[0].item_tax_template;

//                 if (template) {
//                     return frappe.db.get_value(
//                         "Item Tax Template",
//                         template,
//                         "gst_rate"
//                     );
//                 }
//             }

//         }).then(r => {

//             if (r && r.message && r.message.gst_rate) {
//                 frappe.model.set_value(cdt, cdn, "gst_percentage", r.message.gst_rate);
//             } else {
//                 frappe.model.set_value(cdt, cdn, "gst_percentage", 0);
//             }

//             apply_global_discount(frm);
//         });
//     }

// });


// /* =====================================================
// APPLY SAME % TO ALL ROWS
// ===================================================== */

// function apply_global_discount(frm) {

//     if (is_submitted_pos(frm)) {
//         return;
//     }

//     let rows = frm.doc.sku_details || [];

//     let total_price = 0;

//     // =========================================
//     // CALCULATE TOTAL PRICE
//     // =========================================

//     rows.forEach(r => {

//         let row_total = flt(r.price) * flt(r.qty);

//         total_price += row_total;
//     });

//     // store parent total price
//     frm.set_value("total_price", total_price);

//     // =========================================
//     // CALCULATE DISCOUNT %
//     // =========================================

//     let total_discount = flt(frm.doc.total_discount_in_rs);

//     let perc = 0;

//     if (total_price > 0) {
//         perc = (total_discount / total_price) * 100;
//     }

//     frm.set_value("discount_percentage", flt(perc));

//     // =========================================
//     // APPLY DISCOUNT TO ALL ROWS
//     // =========================================

//     rows.forEach(r => {

//         let amount = flt(r.price) * flt(r.qty);

//         let disc = (amount * perc) / 100;

//         let final_amount = amount - disc;

//         if (final_amount < 0) {
//             final_amount = 0;
//         }

//         let gst_amount =
//             (final_amount * flt(r.gst_percentage)) / 100;

//         frappe.model.set_value(
//             r.doctype,
//             r.name,
//             "discount",
//             disc
//         );

//         frappe.model.set_value(
//             r.doctype,
//             r.name,
//             "final_amount",
//             final_amount
//         );

//         frappe.model.set_value(
//             r.doctype,
//             r.name,
//             "gst_amount",
//             gst_amount
//         );
//     });

//     frm.refresh_field("sku_details");

//     calculate_parent_totals(frm);
// }


// /* =====================================================
// TOTALS
// ===================================================== */

// function calculate_parent_totals(frm) {

//     if (is_submitted_pos(frm)) {
//         return;
//     }

//     let total_amount = 0;
//     let total_gst = 0;

//     (frm.doc.sku_details || []).forEach(row => {

//         total_amount += flt(row.final_amount);
//         total_gst += flt(row.gst_amount);

//     });

//     let packing = flt(frm.doc.handling_and_packaging_charges);

//     frm.set_value(
//         "total_amount_wo_tax",
//         total_amount + packing
//     );

//     frm.set_value(
//         "total_amount_with_gst",
//         total_amount + total_gst + packing
//     );

//     calculate_balance(frm);
// }

// /* =====================================================
// PAYMENT
// ===================================================== */

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

//     frm.set_value("paid_amount", paid);

//     calculate_balance(frm);
// }


// /* =====================================================
// BALANCE
// ===================================================== */

// function calculate_balance(frm) {

//     if (is_submitted_pos(frm)) {
//         return;
//     }

//     let total = flt(frm.doc.total_amount_with_gst);
//     let paid = flt(frm.doc.paid_amount);

//     frm.set_value("balance_amount", money(total - paid));
// }


// /* =====================================================
// LOAD
// ===================================================== */

// function calculate_all(frm) {

//     if (is_submitted_pos(frm)) {
//         return;
//     }

//     apply_global_discount(frm);
//     calculate_payments(frm);
// }


// /* =====================================================
// SAFE FLOAT
// ===================================================== */

// function flt(val) {
//     return parseFloat(val) || 0;
// }

// function money(val) {
//     return Math.round((flt(val) + Number.EPSILON) * 100) / 100;
// }

// function is_submitted_pos(frm) {
//     return is_pos(frm) && frm.doc.docstatus === 1;
// }

// function apply_opportunity_client_name(frm) {

//     if (!frm.is_new()) {
//         return;
//     }

//     let pending_client_name = "";

//     try {
//         pending_client_name =
//             sessionStorage.getItem("pending_pos_client_name") || "";
//     } catch (e) {
//         pending_client_name = "";
//     }

//     pending_client_name =
//         pending_client_name ||
//         (frappe.route_options && frappe.route_options.client_name) ||
//         "";

//     if (!pending_client_name) {
//         return;
//     }

//     setTimeout(function () {
//         resolve_and_set_client_name(frm, pending_client_name);
//     }, 300);
// }

// /* =====================================================
// RESOLVE LEAD -> lead_name -> client_name

// Incoming value can be:
//   - a Lead ID (e.g. CRM-LEAD-2026-00026) -> fetch its lead_name
//   - the lead name directly (e.g. Dr Sunanda p) -> used as-is (fallback)
// ===================================================== */
// function resolve_and_set_client_name(frm, value) {

//     let raw = (value || "").trim();

//     if (!frm.is_new() || !raw) {
//         return;
//     }

//     // Try to resolve the value as a Lead and pull its lead_name
//     frappe.db.get_value("Lead", raw, "lead_name").then(function (r) {

//         let lead_name =
//             (r && r.message && r.message.lead_name)
//                 ? r.message.lead_name
//                 : "";

//         // If no matching Lead found, fall back to the raw value
//         let final_name = lead_name || raw;

//         if (frm.is_new() && frm.doc.client_name !== final_name) {
//             frm.set_value("client_name", final_name);
//         }

//         try {
//             sessionStorage.removeItem("pending_pos_client_name");
//         } catch (e) {
//             // browser storage may be unavailable in private contexts
//         }
//     });
// }




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

        // IMPORTANT:
        // preserve route value during initial load

        if (
            frm.is_new() &&
            frappe.route_options &&
            frappe.route_options.client_name &&
            !frm.doc.client_name
        ) {

            frm.set_value(
                "client_name",
                frappe.route_options.client_name
            );
        }

        console.log("CLIENT AFTER:", frm.doc.client_name);
    },

    onload_post_render: function (frm) {
        apply_opportunity_client_name(frm);
    },

    // =========================================
    // REFRESH
    // =========================================

    refresh: function (frm) {

        console.log("POS REFRESH:", frm.doc.client_name);

        if (frm.is_new()) {
            apply_opportunity_client_name(frm);
            return;
        }

        if (frm.doc.docstatus === 1) {

            frm.add_custom_button(__('Sales Return'), function () {

                frappe.model.open_mapped_doc({
                    method: "arnav_customization.arnav_customization.doctype.pos.pos.make_credit_note",
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

        frappe.model.set_value(cdt, cdn, "batch_no", row.sku);

        frappe.db.get_value("SKU", row.sku,
            ["product", "gross_weight", "net_weight"]
        ).then(r => {

            if (!r.message) return;

            let item = r.message.product;

            frappe.model.set_value(cdt, cdn, "product", item);
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

    set_parent_if_changed(
        frm,
        "total_amount_wo_tax",
        money(total_amount + packing),
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

frappe.ui.form.on('POS Payment Details', {

    amount: function (frm) {
        calculate_payments(frm);
    },

    payment_details_remove: function (frm) {
        calculate_payments(frm);
    }

});

function calculate_payments(frm) {

    if (is_submitted_pos(frm)) {
        return;
    }

    let paid = 0;

    (frm.doc.payment_details || []).forEach(row => {
        paid += flt(row.amount);
    });

    set_parent_if_changed(frm, "paid_amount", money(paid), 2);

    calculate_balance(frm);
}

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

function apply_opportunity_client_name(frm) {

    if (!frm.is_new()) {
        return;
    }

    let pending_client_name = "";

    try {
        pending_client_name =
            sessionStorage.getItem("pending_pos_client_name") || "";
    } catch (e) {
        pending_client_name = "";
    }

    pending_client_name =
        pending_client_name ||
        (frappe.route_options && frappe.route_options.client_name) ||
        "";

    if (!pending_client_name) {
        return;
    }

    setTimeout(function () {
        resolve_and_set_client_name(frm, pending_client_name);
    }, 300);
}

/* =====================================================
RESOLVE LEAD -> lead_name -> client_name

Incoming value can be:
  - a Lead ID (e.g. CRM-LEAD-2026-00026) -> fetch its lead_name
  - the lead name directly (e.g. Dr Sunanda p) -> used as-is (fallback)
===================================================== */
function resolve_and_set_client_name(frm, value) {

    let raw = (value || "").trim();

    if (!frm.is_new() || !raw) {
        return;
    }

    frappe.db.get_value("Lead", raw, "lead_name").then(function (r) {

        let lead_name =
            (r && r.message && r.message.lead_name)
                ? r.message.lead_name
                : "";

        let final_name = lead_name || raw;

        if (frm.is_new() && frm.doc.client_name !== final_name) {
            frm.set_value("client_name", final_name);
        }

        try {
            sessionStorage.removeItem("pending_pos_client_name");
        } catch (e) {
            // browser storage may be unavailable in private contexts
        }
    });
}