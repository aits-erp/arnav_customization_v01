frappe.ui.form.on("SKU Master", {
        refresh(frm) {
        frm.add_custom_button(
            __("Get Items From"),
            () => open_multi_invoice_dialog(frm)
        );
    }
});

function open_multi_invoice_dialog(frm) {
    new frappe.ui.form.MultiSelectDialog({
        doctype: "Purchase Invoice",
        target: frm,
        setters: {
            supplier: null,
            posting_date: null
        },
        add_filters_group: 1,
        date_field: "posting_date",
        get_query() {
            return { filters: { docstatus: 1 } };
        },
        action(selections) {
            if (!selections.length) return;

            frappe.confirm(
                __("Replace existing items? Click No to Append."),
                () => load_invoices(frm, selections, true),
                () => load_invoices(frm, selections, false)
            );
        }
    });
}

// function load_invoices(frm, invoice_names, replace) {
//     if (replace) {
//         frm.clear_table("sku_details");
//         frm.clear_table("purchase_invoices");
//     }

//     const existing_item_keys = new Set(
//         (frm.doc.sku_details || []).map(
//             r => `${r.purchase_invoice}::${r.product}`
//         )
//     );

//     let suppliers = new Set();
//     let total_qty = 0;
//     let pending = invoice_names.length;

//     invoice_names.forEach(inv_name => {
//         frappe.call({
//             method: "frappe.client.get",
//             args: {
//                 doctype: "Purchase Invoice",
//                 name: inv_name
//             },
//             callback(r) {
//                 if (!r.message) return;

//                 const inv = r.message;
//                 suppliers.add(inv.supplier);

//                 // Add invoice row
//                 const inv_row = frm.add_child("purchase_invoices");
//                 inv_row.purchase_invoice = inv.name;
//                 inv_row.supplier = inv.supplier;
//                 inv_row.posting_date = inv.posting_date;

//                 // Add items
//                 // (inv.items || []).forEach(item => {
//                 //     const key = `${inv.name}::${item.item_code}`;
//                 //     if (existing_item_keys.has(key)) return;

//                 //     const row = frm.add_child("sku_details");
//                 //     row.product = item.item_code;
//                 //     row.qty = item.qty;
//                 //     row.cost_price = item.rate;
//                 //     row.purchase_invoice = inv.name;
//                 //     row.purchase_invoice_item = item.name;

//                 //     total_qty += flt(item.qty);
//                 //     existing_item_keys.add(key);
//                 // });

//                 (inv.items || []).forEach(item => {
//                     total_qty += flt(item.qty);
//                 });

//                 pending--;

//                 // FINALIZE ONCE
//                 if (pending === 0) {
//                     finalize_form(frm, suppliers, total_qty);
//                 }
//             }
//         });
//     });
// }
function load_invoices(frm, invoice_names, replace) {

    if (!invoice_names || !invoice_names.length) return;

    // Always take ONLY the first invoice (client requirement)
    const first_invoice = invoice_names[0];

    // Since only single invoice allowed, clear table
    frm.clear_table("purchase_invoices");

    frappe.call({
        method: "frappe.client.get",
        args: {
            doctype: "Purchase Invoice",
            name: first_invoice
        },
        callback(r) {
            if (!r.message) return;

            const inv = r.message;

            // -----------------------------
            // 1️⃣ Add Purchase Invoice row
            // -----------------------------
            const inv_row = frm.add_child("purchase_invoices");
            inv_row.purchase_invoice = inv.name;
            inv_row.supplier = inv.supplier;
            inv_row.posting_date = inv.posting_date;

            frm.refresh_field("purchase_invoices");

            // -----------------------------
            // 2️⃣ Fetch Header Fields
            // -----------------------------
            frm.set_value("supplier_name", inv.supplier);
            frm.set_value("invoice_no", inv.name);
            frm.set_value("date_of_invoice", inv.posting_date);
            frm.set_value("warehouse", inv.set_warehouse || inv.items?.[0]?.warehouse || "");
            frm.set_value("metal", inv.metal || "");
            frm.set_value("hsn", inv.hsn || "");

            // -----------------------------
            // 3️⃣ Calculate Net Quantity
            // -----------------------------
            let total_qty = 0;

            (inv.items || []).forEach(item => {
                total_qty += flt(item.qty);
            });

            frm.set_value("net_quantiity", total_qty);

            // -----------------------------
            // 4️⃣ Refresh Header Fields
            // -----------------------------
            frm.refresh_fields([
                "supplier_name",
                "invoice_no",
                "date_of_invoice",
                "warehouse",
                "metal",
                "hsn",
                "net_quantiity"
            ]);
        }
    });
}


function finalize_form(frm, suppliers, total_qty) {
    frm.set_value("net_quantiity", total_qty);

    if (suppliers.size === 1) {
        frm.set_value("supplier_name", [...suppliers][0]);
    } else {
        frm.set_value("supplier_name", __("Multiple Suppliers"));
    }

    // ONE authoritative refresh
    frm.refresh_field("purchase_invoices");
    frm.refresh_field("sku_details");
    frm.refresh_field("net_quantiity");
    frm.refresh_field("supplier_name");
}

