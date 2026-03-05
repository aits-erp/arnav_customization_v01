frappe.ui.form.on('POS', {

    refresh: function(frm) {
        calculate_all(frm);
    },

    before_submit: function(frm) {

        let balance = flt(frm.doc.balance_amount);

        if (Math.abs(balance) > 0.01) {
            frappe.throw({
                title: __("Submission Not Allowed"),
                message: __("Cannot submit POS because Balance Amount must be 0.00. Current Balance: ") + balance
            });
        }

        const CASH_LIMIT = 195000;
        let total_cash = 0;

        (frm.doc.payment_details || []).forEach(row => {

            if (row.payment_type === "Cash") {

                let row_amount = flt(row.amount);

                if (row_amount > CASH_LIMIT) {
                    frappe.throw({
                        title: __("Cash Limit Exceeded"),
                        message: __("Single Cash entry cannot exceed ₹") + CASH_LIMIT +
                                __(". Current Row Amount: ₹") + row_amount
                    });
                }

                total_cash += row_amount;
            }
        });

        if (total_cash > CASH_LIMIT) {
            frappe.throw({
                title: __("Cash Limit Exceeded"),
                message: __("Total Cash payment cannot exceed ₹") + CASH_LIMIT +
                        __(". Total Cash Entered: ₹") + total_cash
            });
        }
    },

    setup: function(frm) {
        frm.set_query("client_name", function() {
            return {
                query: "arnav_customization.arnav_customization.doctype.pos.pos.customer_search_by_mobile"
            };
        });
    }

});



/* =====================================================
SKU TABLE LOGIC
===================================================== */

frappe.ui.form.on('POS SKU Details', {

    price: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },

    qty: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },

    discount: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },

    gst_percentage: function(frm, cdt, cdn) {
        calculate_row(frm, cdt, cdn);
    },

    sku_details_remove: function(frm) {
        calculate_parent_totals(frm);
    },


    /* ======================================
    SKU SELECTED
    ====================================== */

    sku: function(frm, cdt, cdn) {

        let row = locals[cdt][cdn];
        if (!row.sku) return;

        // STEP 1 — Get product + weights from SKU
        frappe.db.get_value("SKU", row.sku,
            ["product", "gross_weight", "net_weight"]
        ).then(r => {

            if (!r.message) return;

            let item = r.message.product;

            frappe.model.set_value(cdt, cdn, "product", item);
            frappe.model.set_value(cdt, cdn, "gross_weight", r.message.gross_weight);
            frappe.model.set_value(cdt, cdn, "net_weight", r.message.net_weight);

            // STEP 2 — Get Item (HSN + tax template)
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

            calculate_row(frm, cdt, cdn);

        });
    }

});



/* =====================================================
ROW CALCULATION
===================================================== */

function calculate_row(frm, cdt, cdn) {

    let row = locals[cdt][cdn];

    let price = flt(row.price);
    let qty = flt(row.qty);
    let discount = flt(row.discount);
    let gst = flt(row.gst_percentage);

    let final_amount = (price * qty) - discount;

    frappe.model.set_value(cdt, cdn, "final_amount", final_amount);

    let gst_amount = (final_amount * gst) / 100;

    frappe.model.set_value(cdt, cdn, "gst_amount", gst_amount);

    calculate_parent_totals(frm);
}



/* =====================================================
PARENT TOTALS
===================================================== */

function calculate_parent_totals(frm) {

    let total_discount = 0;
    let total_amount = 0;
    let total_gst = 0;

    (frm.doc.sku_details || []).forEach(row => {

        total_discount += flt(row.discount);
        total_amount += flt(row.final_amount);
        total_gst += flt(row.gst_amount);

    });

    frm.set_value("total_discount_in_rs", total_discount);
    frm.set_value("total_amount_wo_tax", total_amount);
    frm.set_value("total_amount_with_gst", total_amount + total_gst);

    calculate_balance(frm);
}



/* =====================================================
PAYMENT TABLE
===================================================== */

frappe.ui.form.on('POS Payment Details', {

    amount: function(frm) {
        calculate_payments(frm);
    },

    payment_details_remove: function(frm) {
        calculate_payments(frm);
    }

});


function calculate_payments(frm) {

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

    let total = flt(frm.doc.total_amount_with_gst);
    let paid = flt(frm.doc.paid_amount);

    frm.set_value("balance_amount", total - paid);
}



/* =====================================================
FLOAT SAFE
===================================================== */

function flt(val) {
    return parseFloat(val) || 0;
}


function calculate_all(frm) {
    calculate_parent_totals(frm);
    calculate_payments(frm);
}

// frappe.ui.form.on('POS', {
//     refresh: function(frm) {
//         calculate_all(frm);
//     },

//     // before_submit: function(frm) {

//     //     let balance = flt(frm.doc.balance_amount);

//     //     if (Math.abs(balance) > 0.01) {
//     //         frappe.throw({
//     //             title: __("Submission Not Allowed"),
//     //             message: __("Cannot submit POS because Balance Amount must be 0.00. Current Balance: ") + balance
//     //         });
//     //     }
//     // }
//     before_submit: function(frm) {

//         let balance = flt(frm.doc.balance_amount);

//         if (Math.abs(balance) > 0.01) {
//             frappe.throw({
//                 title: __("Submission Not Allowed"),
//                 message: __("Cannot submit POS because Balance Amount must be 0.00. Current Balance: ") + balance
//             });
//         }

//         // ===============================
//         // CASH LIMIT VALIDATION
//         // ===============================

//         const CASH_LIMIT = 195000;
//         let total_cash = 0;

//         (frm.doc.payment_details || []).forEach(row => {

//             if (row.payment_type === "Cash") {

//                 let row_amount = flt(row.amount);

//                 // Individual row validation
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

//         // Total cash validation (handles split rows)
//         if (total_cash > CASH_LIMIT) {
//             frappe.throw({
//                 title: __("Cash Limit Exceeded"),
//                 message: __("Total Cash payment cannot exceed ₹") + CASH_LIMIT +
//                         __(". Total Cash Entered: ₹") + total_cash
//             });
//         }
//     },

//     setup: function(frm) {
//         frm.set_query("client_name", function() {
//             return {
//                 query: "arnav_customization.arnav_customization.doctype.pos.pos.customer_search_by_mobile"
//             };
//         });
//     }
// });

// // ===============================
// // SKU TABLE CALCULATIONS
// // ===============================

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
//     sku_details_remove: function(frm) {
//         calculate_parent_totals(frm);
//     },

//     sku: function(frm, cdt, cdn) {
//         let row = locals[cdt][cdn];

//         if (!row.sku) return;

//         // Step 1: Get product (Item) from SKU
//         frappe.db.get_value('SKU', row.sku, 'product')
//             .then(r => {

//                 if (r.message && r.message.product) {

//                     let item = r.message.product;

//                     // Set product field
//                     frappe.model.set_value(cdt, cdn, 'product', item);

//                     // Step 2: Get HSN from Item
//                     return frappe.db.get_value('Item', item, 'gst_hsn_code');

//                 }
//             })
//             .then(r => {

//                 if (r && r.message && r.message.gst_hsn_code) {
//                     frappe.model.set_value(cdt, cdn, 'hsn', r.message.gst_hsn_code);
//                 }

//             });

//         // Recalculate
//         calculate_row(frm, cdt, cdn);
//     }
// });

// function calculate_row(frm, cdt, cdn) {
//     let row = locals[cdt][cdn];

//     let price = flt(row.price);
//     let qty = flt(row.qty);
//     let discount = flt(row.discount);

//     row.final_amount = (price * qty) - discount;

//     frappe.model.set_value(cdt, cdn, "final_amount", row.final_amount);

//     calculate_parent_totals(frm);
// }

// function calculate_parent_totals(frm) {

//     let total_discount = 0;
//     let total_amount = 0;

//     (frm.doc.sku_details || []).forEach(row => {
//         total_discount += flt(row.discount);
//         total_amount += flt(row.final_amount);
//     });

//     frm.set_value("total_discount_in_rs", total_discount);
//     frm.set_value("total_amount_wo_tax", total_amount);

//     calculate_balance(frm);
// }

// // ===============================
// // PAYMENT TABLE CALCULATIONS
// // ===============================

// frappe.ui.form.on('POS Payment Details', {
//     amount: function(frm) {
//         calculate_payments(frm);
//     },
//     payment_details_remove: function(frm) {
//         calculate_payments(frm);
//     }
// });

// function calculate_payments(frm) {

//     let paid = 0;

//     (frm.doc.payment_details || []).forEach(row => {
//         paid += flt(row.amount);
//     });

//     frm.set_value("paid_amount", paid);

//     calculate_balance(frm);
// }

// // ===============================
// // BALANCE CALCULATION
// // ===============================

// function calculate_balance(frm) {

//     let total = flt(frm.doc.total_amount_wo_tax);
//     let paid = flt(frm.doc.paid_amount);

//     frm.set_value("balance_amount", total - paid);
// }

// // ===============================
// // FLOAT SAFE
// // ===============================

// function flt(val) {
//     return parseFloat(val) || 0;
// }

// function calculate_all(frm) {
//     calculate_parent_totals(frm);
//     calculate_payments(frm);
// }