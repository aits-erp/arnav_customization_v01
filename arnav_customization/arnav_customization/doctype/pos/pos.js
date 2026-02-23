// Copyright (c) 2026, aits and contributors
// For license information, please see license.txt

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
    }
});

// ===============================
// SKU TABLE CALCULATIONS
// ===============================

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
    sku_details_remove: function(frm) {
        calculate_parent_totals(frm);
    }
});

function calculate_row(frm, cdt, cdn) {
    let row = locals[cdt][cdn];

    let price = flt(row.price);
    let qty = flt(row.qty);
    let discount = flt(row.discount);

    row.final_amount = (price * qty) - discount;

    frappe.model.set_value(cdt, cdn, "final_amount", row.final_amount);

    calculate_parent_totals(frm);
}

function calculate_parent_totals(frm) {

    let total_discount = 0;
    let total_amount = 0;

    (frm.doc.sku_details || []).forEach(row => {
        total_discount += flt(row.discount);
        total_amount += flt(row.final_amount);
    });

    frm.set_value("total_discount_in_rs", total_discount);
    frm.set_value("total_amount_wo_tax", total_amount);

    calculate_balance(frm);
}

// ===============================
// PAYMENT TABLE CALCULATIONS
// ===============================

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

// ===============================
// BALANCE CALCULATION
// ===============================

function calculate_balance(frm) {

    let total = flt(frm.doc.total_amount_wo_tax);
    let paid = flt(frm.doc.paid_amount);

    frm.set_value("balance_amount", total - paid);
}

// ===============================
// FLOAT SAFE
// ===============================

function flt(val) {
    return parseFloat(val) || 0;
}
