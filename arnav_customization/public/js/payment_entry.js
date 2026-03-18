frappe.ui.form.on('Payment Entry', {
    refresh(frm) {
        calculate_total(frm);
    }
});

frappe.ui.form.on('POS Payment Details', {
    amount(frm, cdt, cdn) {
        calculate_total(frm);
    },
    custom_payment_details_table_remove(frm) {
        calculate_total(frm);
    }
});

function calculate_total(frm) {
    let total = 0;

    (frm.doc.custom_payment_details_table || []).forEach(row => {
        total += flt(row.amount);
    });

    frm.set_value('paid_amount', total);
}