frappe.ui.form.on('Payment Entry', {

    // After party selection → accounts + currency set
    party: function(frm) {
        calculate_total(frm);
    },

    // When accounts change → currency ready
    paid_from: function(frm) {
        calculate_total(frm);
    },

    paid_to: function(frm) {
        calculate_total(frm);
    },

    // When exchange rate is set → system stabilized
    source_exchange_rate: function(frm) {
        calculate_total(frm);
    },

    target_exchange_rate: function(frm) {
        calculate_total(frm);
    },

    // Final safety
    refresh: function(frm) {
        calculate_total(frm);
    }
});

frappe.ui.form.on('POS Payment Details', {

    amount(frm) {
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

    // ================================
    // POS → direct update (safe)
    // ================================
    if (frm.doc.doctype === "POS") {
        frm.set_value('paid_amount', total);
        return;
    }

    // ================================
    // PAYMENT ENTRY → controlled override
    // ================================
    if (frm.doc.doctype === "Payment Entry") {

        // 🚨 HARD GUARD: currencies must exist
        if (!frm.doc.paid_from_account_currency || !frm.doc.paid_to_account_currency) {
            console.warn("Skip override: currencies not ready");
            return;
        }

        // 🚨 HARD GUARD: accounts must exist
        if (!frm.doc.paid_from || !frm.doc.paid_to) {
            console.warn("Skip override: accounts not set");
            return;
        }

        try {
            // ✅ Set both fields (critical for ERPNext consistency)
            frm.set_value({
                paid_amount: total,
                received_amount: total
            });

        } catch (e) {
            console.error("Failed to set payment values", e);
            frappe.msgprint({
                title: "Calculation Warning",
                message: "Unable to sync payment amounts. Please re-check values.",
                indicator: "orange"
            });
        }
    }
}