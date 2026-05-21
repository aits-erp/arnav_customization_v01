// function is_pos(frm) {
//     return frm.doc.doctype === "POS";
// }

// frappe.ui.form.on('POS', {

//     setup: function(frm) {

//         // ============================================
//         // FILTER SKU ITEMS BASED ON METAL
//         // ============================================

//         frm.set_query("product", "sku_details", function(doc) {

//             if (!doc.billtype) {
//                 return { filters: { name: "" } };
//             }

//             return {
//                 filters: {
//                     custom_metal: doc.billtype
//                 }
//             };
//         });

//         // ============================================
//         // CREDIT NOTE FILTER BASED ON CUSTOMER ON POS
//         // ============================================
//         frm.set_query("credit_note", "payment_details", function(doc, cdt, cdn) {
//             return {
//                 filters: {
//                     customer: doc.client_name
//                 }
//             };
//         });

//         // ============================================
//         // FILTER PACKING MATERIAL ITEMS
//         // ============================================

//         frm.set_query("packing_material", "packing_materials", function() {

//             return {
//                 filters: {
//                     item_group: "Packing"
//                 }
//             };
//         });


//         // Existing customer query
//         frm.set_query("client_name", function() {
//             return {
//                 query: "arnav_customization.arnav_customization.doctype.pos.pos.customer_search_by_mobile"
//             };
//         });

//     },

//     refresh: function(frm) {
//         calculate_all(frm);

//         if (!frm.is_new() && frm.doc.docstatus === 1) {

//             frm.add_custom_button(__('Sales Return'), function () {

//                 frappe.model.open_mapped_doc({
//                     method: "arnav_customization.arnav_customization.doctype.pos.pos.make_credit_note",
//                     frm: frm
//                 });

//             }, __("Create"));
//         }
//     },

//     before_submit: function(frm) {

//         let balance = flt(frm.doc.balance_amount);

//         if (Math.abs(balance) > 0.01) {
//             frappe.throw({
//                 title: __("Submission Not Allowed"),
//                 message: __("Cannot submit POS because Balance Amount must be 0.00. Current Balance: ") + balance
//             });
//         }

//         const CASH_LIMIT = 195000;
//         let total_cash = 0;

//         (frm.doc.payment_details || []).forEach(row => {

//             if (row.payment_type === "Cash") {

//                 let row_amount = flt(row.amount);

//                 if (row_amount > CASH_LIMIT) {
//                     frappe.throw({
//                         title: __("Cash Limit Exceeded"),
//                         message: __("Single Cash entry cannot exceed ₹") + CASH_LIMIT +
//                                 __(". Current Row Amount: ₹") + row_amount
//                     });
//                 }

//                 total_cash += row_amount;
//             }
//         });

//         if (total_cash > CASH_LIMIT) {
//             frappe.throw({
//                 title: __("Cash Limit Exceeded"),
//                 message: __("Total Cash payment cannot exceed ₹") + CASH_LIMIT +
//                         __(". Total Cash Entered: ₹") + total_cash
//             });
//         }
//     },

//     client_name: function(frm) {
//         // refresh child table filter when customer changes
//         frm.refresh_field("payment_details");
//     }

// });

// /* =====================================================
// SKU TABLE LOGIC
// ===================================================== */

// frappe.ui.form.on('POS SKU Details', {

//     price: function(frm, cdt, cdn) {
//         calculate_row(frm, cdt, cdn);
//     },

//     qty: function(frm, cdt, cdn) {
//         calculate_row(frm, cdt, cdn);
//     },

//     discount: function(frm, cdt, cdn) {
//         calculate_row(frm, cdt, cdn);
//     },

//     gst_percentage: function(frm, cdt, cdn) {
//         calculate_row(frm, cdt, cdn);
//     },

//     sku_details_remove: function(frm) {
//         calculate_parent_totals(frm);
//     },


//     /* ======================================
//     SKU SELECTED
//     ====================================== */

//     sku: function(frm, cdt, cdn) {

//         let row = locals[cdt][cdn];
//         if (!row.sku) return;

//         // IMPORTANT: SKU == Batch
//         frappe.model.set_value(cdt, cdn, "batch_no", row.sku);

//         // STEP 1 — Get product + weights from SKU
//         frappe.db.get_value("SKU", row.sku,
//             ["product", "gross_weight", "net_weight"]
//         ).then(r => {

//             if (!r.message) return;

//             let item = r.message.product;

//             frappe.model.set_value(cdt, cdn, "product", item);
//             frappe.model.set_value(cdt, cdn, "gross_weight", r.message.gross_weight);
//             frappe.model.set_value(cdt, cdn, "net_weight", r.message.net_weight);

//             // STEP 2 — Get Item (HSN + tax template)
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

//             calculate_row(frm, cdt, cdn);

//         });
//     }

// });



// /* =====================================================
// ROW CALCULATION
// ===================================================== */

// function calculate_row(frm, cdt, cdn) {

//     let row = locals[cdt][cdn];

//     let price = flt(row.price);
//     let qty = flt(row.qty);
//     let discount = flt(row.discount);
//     let gst = flt(row.gst_percentage);

//     let final_amount = (price * qty) - discount;

//     frappe.model.set_value(cdt, cdn, "final_amount", final_amount);

//     let gst_amount = (final_amount * gst) / 100;

//     frappe.model.set_value(cdt, cdn, "gst_amount", gst_amount);

//     calculate_parent_totals(frm);
// }



// /* =====================================================
// PARENT TOTALS
// ===================================================== */

// function calculate_parent_totals(frm) {
//     if (!is_pos(frm)) return;

//     let total_discount = 0;
//     let total_amount = 0;
//     let total_gst = 0;

//     (frm.doc.sku_details || []).forEach(row => {

//         total_discount += flt(row.discount);
//         total_amount += flt(row.final_amount);
//         total_gst += flt(row.gst_amount);

//     });

//     frm.set_value("total_discount_in_rs", total_discount);
//     frm.set_value("total_amount_wo_tax", total_amount);
//     frm.set_value("total_amount_with_gst", total_amount + total_gst);

//     calculate_balance(frm);
// }



// /* =====================================================
// PAYMENT TABLE
// ===================================================== */

// frappe.ui.form.on('POS Payment Details', {

//     amount: function(frm, cdt, cdn) {
//         calculate_payments(frm);
//     },

//     payment_details_remove: function(frm) {
//         calculate_payments(frm);
//     },

//     payment_type: function(frm, cdt, cdn) {
//         if (frm.doc.doctype !== "POS") return;

//         let row = locals[cdt][cdn];

//         if (row.payment_type !== "Old Gold") {
//             frappe.model.set_value(cdt, cdn, "credit_note", null);
//             frappe.model.set_value(cdt, cdn, "amount", null);
//         }
//     },

//     credit_note: function(frm, cdt, cdn) {
//         if (frm.doc.doctype !== "POS") return;

//         let row = locals[cdt][cdn];

//         if (row.credit_note) {
//             frappe.db.get_doc('Credit Note', row.credit_note)
//                 .then(doc => {
//                     frappe.model.set_value(cdt, cdn, "amount", doc.grand_total || doc.total || 0);
//                 });
//         }
//     }
// });


// function calculate_payments(frm) {

//     let paid = 0;

//     (frm.doc.payment_details || []).forEach(row => {
//         paid += flt(row.amount);
//     });

//     // 🚨 ONLY FOR POS
//     if (is_pos(frm)) {
//         frm.set_value("paid_amount", paid);
//         calculate_balance(frm);
//     }

//     // ✅ For other doctypes → do nothing (prevents exchange rate crash)
// }

// /* =====================================================
// BALANCE
// ===================================================== */

// function calculate_balance(frm) {

//     // 🚨 ADD THIS
//     if (!is_pos(frm)) return;

//     let total = flt(frm.doc.total_amount_with_gst);
//     let paid = flt(frm.doc.paid_amount);

//     frm.set_value("balance_amount", total - paid);
// }

// /* =====================================================
// FLOAT SAFE
// ===================================================== */

// function flt(val) {
//     return parseFloat(val) || 0;
// }

// function calculate_all(frm) {

//     if (is_pos(frm)) {
//         calculate_parent_totals(frm);
//     }

//     calculate_payments(frm); // safe now
// }


function is_pos(frm) {
    return frm.doc.doctype === "POS";
}

/* =====================================================
POS MAIN FORM
===================================================== */

// frappe.ui.form.on('POS', {

//     setup: function(frm) {

//         frm.set_query("product", "sku_details", function(doc) {
//             if (!doc.billtype) {
//                 return { filters: { name: "" } };
//             }

//             return {
//                 filters: {
//                     custom_metal: doc.billtype
//                 }
//             };
//         });

//         frm.set_query("credit_note", "payment_details", function(doc) {
//             return {
//                 filters: {
//                     customer: doc.client_name
//                 }
//             };
//         });

//         frm.set_query("packing_material", "packing_materials", function() {
//             return {
//                 filters: {
//                     // item_group: "Packing"
//                     item_group: "PACKING METERIALS"

//                 }
//             };
//         });

//         frm.set_query("client_name", function() {
//             return {
//                 query: "arnav_customization.arnav_customization.doctype.pos.pos.customer_search_by_mobile"
//             };
//         });
//     },


//     refresh: function(frm) {

//         // Prevent calculations during initial new doc creation
//         if (frm.is_new()) {
//             return;
//         }

//         calculate_all(frm);

//         if (!frm.is_new() && frm.doc.docstatus === 1) {
//             frm.add_custom_button(__('Sales Return'), function () {
//                 frappe.model.open_mapped_doc({
//                     method: "arnav_customization.arnav_customization.doctype.pos.pos.make_credit_note",
//                     frm: frm
//                 });
//             }, __("Create"));
//         }
//     },

//     before_submit: function(frm) {

//         let balance = flt(frm.doc.balance_amount);

//         if (Math.abs(balance) > 0.01) {
//             frappe.throw({
//                 title: __("Submission Not Allowed"),
//                 message: __("Cannot submit POS because Balance Amount must be 0.00. Current Balance: ") + balance
//             });
//         }
//     },

//     handling_and_packaging_charges: function(frm) {
//         calculate_parent_totals(frm);
//     },

//     total_discount_in_rs: function(frm) {
//         apply_global_discount(frm);
//     },

// });

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

        // =========================================
        // CLIENT NAME QUERY
        // =========================================

        frm.set_query("client_name", function () {

            return {
                query: "arnav_customization.arnav_customization.doctype.pos.pos.customer_search_by_mobile"
            };
        });
    },

    // =========================================
    // ONLOAD
    // =========================================

    // onload: function(frm) {

    //     console.log("POS ONLOAD");

    //     console.log("CLIENT BEFORE:", frm.doc.client_name);

    //     // IMPORTANT:
    //     // preserve route value during initial load

    //     if (
    //         frm.is_new() &&
    //         frappe.route_options &&
    //         frappe.route_options.client_name &&
    //         !frm.doc.client_name
    //     ) {

    //         frm.set_value(
    //             "client_name",
    //             frappe.route_options.client_name
    //         );
    //     }

    //     console.log("CLIENT AFTER:", frm.doc.client_name);
    // },


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

                    if (r.message && r.message.branch) {

                        frm.set_value(
                            "branch",
                            r.message.branch
                        );

                        // OPTIONAL:
                        // make branch readonly

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

        // IMPORTANT:
        // avoid calculations while new doc initializing

        if (frm.is_new()) {
            apply_opportunity_client_name(frm);
            return;
        }

        if (!frm.is_new() && frm.doc.docstatus === 1) {

            frm.add_custom_button(__('Sales Return'), function () {

                frappe.model.open_mapped_doc({
                    method: "arnav_customization.arnav_customization.doctype.pos.pos.make_credit_note",
                    frm: frm
                });

            }, __("Create"));

            return;
        }

        calculate_all(frm);
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

    // /* =================================================
    // ONLY FIRST ROW DISCOUNT ENTRY
    // converts to %
    // then applies same % to all rows
    // ================================================= */
    // discount: function(frm, cdt, cdn) {

    //     let row = locals[cdt][cdn];
    //     let rows = frm.doc.sku_details || [];

    //     if (!rows.length) return;

    //     let first_row = rows[0];

    //     if (row.name === first_row.name) {

    //         let amount = flt(first_row.price) * flt(first_row.qty);
    //         let disc = flt(first_row.discount);

    //         let perc = 0;

    //         if (amount > 0) {
    //             perc = (disc / amount) * 100;
    //         }

    //         frm.set_value("discount_percentage", perc);

    //         apply_global_discount(frm);

    //     } else {

    //         apply_global_discount(frm);
    //     }
    // },

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
APPLY SAME % TO ALL ROWS
===================================================== */

// function apply_global_discount(frm) {

//     let rows = frm.doc.sku_details || [];
//     let perc = flt(frm.doc.discount_percentage);

//     rows.forEach(r => {

//         let amount = flt(r.price) * flt(r.qty);

//         let disc = (amount * perc) / 100;

//         // r.discount = disc;

//         // let final_amount = amount - disc;

//         // if (final_amount < 0) final_amount = 0;

//         // r.final_amount = final_amount;

//         // r.gst_amount = (final_amount * flt(r.gst_percentage)) / 100;

//         let final_amount = amount - disc;

//         if (final_amount < 0) {
//             final_amount = 0;
//         }

//         let gst_amount = (final_amount * flt(r.gst_percentage)) / 100;

//         frappe.model.set_value(r.doctype, r.name, "discount", disc);
//         frappe.model.set_value(r.doctype, r.name, "final_amount", final_amount);
//         frappe.model.set_value(r.doctype, r.name, "gst_amount", gst_amount);
//     });

//     frm.refresh_field("sku_details");

//     calculate_parent_totals(frm);
// }

function apply_global_discount(frm) {

    if (is_submitted_pos(frm)) {
        return;
    }

    let rows = frm.doc.sku_details || [];

    let total_price = 0;

    // =========================================
    // CALCULATE TOTAL PRICE
    // =========================================

    rows.forEach(r => {

        let row_total = flt(r.price) * flt(r.qty);

        total_price += row_total;
    });

    // store parent total price
    frm.set_value("total_price", total_price);

    // =========================================
    // CALCULATE DISCOUNT %
    // =========================================

    let total_discount = flt(frm.doc.total_discount_in_rs);

    let perc = 0;

    if (total_price > 0) {
        perc = (total_discount / total_price) * 100;
    }

    frm.set_value("discount_percentage", flt(perc));

    // =========================================
    // APPLY DISCOUNT TO ALL ROWS
    // =========================================

    rows.forEach(r => {

        let amount = flt(r.price) * flt(r.qty);

        let disc = (amount * perc) / 100;

        let final_amount = amount - disc;

        if (final_amount < 0) {
            final_amount = 0;
        }

        let gst_amount =
            (final_amount * flt(r.gst_percentage)) / 100;

        frappe.model.set_value(
            r.doctype,
            r.name,
            "discount",
            disc
        );

        frappe.model.set_value(
            r.doctype,
            r.name,
            "final_amount",
            final_amount
        );

        frappe.model.set_value(
            r.doctype,
            r.name,
            "gst_amount",
            gst_amount
        );
    });

    frm.refresh_field("sku_details");

    calculate_parent_totals(frm);
}


/* =====================================================
TOTALS
===================================================== */

// function calculate_parent_totals(frm) {

//     // let total_discount = 0;
//     let total_amount = 0;
//     let total_gst = 0;

//     (frm.doc.sku_details || []).forEach(row => {

//         // total_discount += flt(row.discount);
//         total_amount += flt(row.final_amount);
//         total_gst += flt(row.gst_amount);

//     });

//     let packing = flt(frm.doc.handling_and_packaging_charges);

//     // frm.set_value("total_discount_in_rs", total_discount);
//     frm.set_value("total_amount_wo_tax", total_amount + packing);
//     frm.set_value("total_amount_with_gst", total_amount + total_gst + packing);

//     calculate_balance(frm);
// }

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

    frm.set_value(
        "total_amount_wo_tax",
        total_amount + packing
    );

    frm.set_value(
        "total_amount_with_gst",
        total_amount + total_gst + packing
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

    frm.set_value("paid_amount", paid);

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

    frm.set_value("balance_amount", money(total - paid));
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

function resolve_and_set_client_name(frm, value) {

    let client_name = (value || "").trim();

    if (!frm.is_new() || !client_name) {
        return;
    }

    frappe.db.get_value("Customer", client_name, "name")
        .then(function (r) {
            if (r.message && r.message.name) {
                return r.message.name;
            }

            return frappe.db.get_value(
                "Customer",
                { customer_name: client_name },
                "name"
            ).then(function (customer) {
                return customer.message && customer.message.name;
            });
        })
        .then(function (customer_name) {
            if (!customer_name || frm.doc.client_name === customer_name) {
                return;
            }

            frm.set_value("client_name", customer_name);

            try {
                sessionStorage.removeItem("pending_pos_client_name");
            } catch (e) {
                // browser storage may be unavailable in private contexts
            }
        });
}
