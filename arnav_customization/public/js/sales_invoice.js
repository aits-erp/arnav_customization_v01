frappe.ui.form.on('Sales Invoice', {

    refresh(frm) {

        // Keep custom calculation fields visible in Sales Invoice Item grid.
        const fields_to_show = [
            "custom_custom_fields",
            "custom_weight",
            "custom_purity",
            "custom_custom_rate"
        ];

        if (frm.fields_dict.items && frm.fields_dict.items.grid) {

            fields_to_show.forEach(field => {

                frm.fields_dict.items.grid.update_docfield_property(
                    field,
                    "hidden",
                    0
                );

            });

            frm.refresh_field("items");
        }

        restore_pos_return_pricing(frm);
    }
});


// =====================================================
// SALES INVOICE ITEM EVENTS
// =====================================================

frappe.ui.form.on("Sales Invoice Item", {

    custom_weight(frm, cdt, cdn) {
        calculate_custom_rate(frm, cdt, cdn);
    },

    custom_custom_rate(frm, cdt, cdn) {
        calculate_custom_rate(frm, cdt, cdn);
    },

    custom_purity(frm, cdt, cdn) {
        calculate_custom_rate(frm, cdt, cdn);
    },

    custom_sku: function(frm, cdt, cdn) {

        // A mapped POS return already contains the original item, quantity,
        // warehouse, batch and historical price.  Fetching the current SKU
        // again here is asynchronous and can overwrite those values after
        // the return form first renders.
        if (frm.doc.is_return && frm.doc.custom_pos) {
            return;
        }

        let row = locals[cdt][cdn];

        if (!row.custom_sku) return;

        frappe.call({

            method: "arnav_customization.sku_mapping_backend.sku_mapper.get_sku_data",

            args: {
                sku: row.custom_sku
            },

            callback: function(r) {

                if (!r.message) return;

                let d = r.message;

                frappe.model.set_value(cdt, cdn, "item_code", d.item_code);

                frappe.model.set_value(cdt, cdn, "qty", d.gross_weight);

                frappe.model.set_value(cdt, cdn, "custom_net_weight", d.net_weight);

                frappe.model.set_value(cdt, cdn, "custom_quantity", d.qty);

                setTimeout(() => {

                    // FIXED
                    frappe.model.set_value(cdt, cdn, "rate", d.rate);

                }, 300);

                frappe.model.set_value(cdt, cdn, "gst_hsn_code", d.hsn);

                frappe.model.set_value(cdt, cdn, "warehouse", d.warehouse);

                frappe.model.set_value(cdt, cdn, "batch_no", d.batch_no);

            }
        });
    }
});


// =====================================================
// CUSTOM RATE CALCULATION
// =====================================================

function calculate_custom_rate(frm, cdt, cdn) {

    // POS returns already arrive with a historical, fully calculated price.
    // Do not run the jewellery weight/purity formula on those mapped rows.
    // This handler runs after the mapped document opens, which was replacing
    // valid POS rates a moment later for only the rows with custom values.
    if (frm.doc.is_return && frm.doc.custom_pos) {
        return;
    }

    let row = locals[cdt][cdn];

    let weight = flt(row.custom_weight);
    let rate = flt(row.custom_custom_rate);
    let purity = flt(row.custom_purity);

    if (weight && rate && purity) {

        let calculated_rate = weight * rate * purity;

        // force qty = 1
        frappe.model.set_value(cdt, cdn, "qty", 1);

        // set calculated value
        frappe.model.set_value(cdt, cdn, "rate", calculated_rate);
    }
}

function restore_pos_return_pricing(frm) {
    if (!frm.is_new() || !frm.doc.is_return || !frm.doc.custom_pos || frm.__restoring_pos_return_pricing) {
        return;
    }

    frm.__restoring_pos_return_pricing = true;
    frappe.call({
        method: "arnav_customization.arnav_customization.doctype.pos.pos.get_pos_return_pricing",
        args: { source_name: frm.doc.custom_pos },
        callback(r) {
            const pricingBySku = r.message || {};
            const applyPricing = () => {
                (frm.doc.items || []).forEach(row => {
                    const pricing = pricingBySku[row.custom_sku];
                    if (!pricing) return;

                    const grossRate = flt(pricing.gross_rate);
                    const unitDiscount = flt(pricing.discount) / (flt(pricing.qty) || 1);

                    row.custom_custom_rate = grossRate;
                    row.price_list_rate = grossRate;
                    row.rate_with_margin = grossRate;
                    row.discount_amount = unitDiscount;
                    row.discount_percentage = grossRate ? (unitDiscount / grossRate) * 100 : 0;
                    row.rate = flt(pricing.effective_rate);
                });

                if (frm.cscript.calculate_taxes_and_totals) {
                    frm.cscript.calculate_taxes_and_totals();
                }
                frm.refresh_field("items");
                frm.__restoring_pos_return_pricing = false;
            };

            // Let ERPNext's outstanding Item Price requests finish first, then
            // restore the immutable transaction values from the POS record.
            frappe.after_ajax(() => setTimeout(applyPricing, 0));
        },
        error() {
            frm.__restoring_pos_return_pricing = false;
        }
    });
}

// frappe.ui.form.on('Sales Invoice', {
//     refresh(frm) {

//         const fields_to_hide = [
//             "custom_custom_fields",
//             "custom_weight",
//             "custom_purity",
//             "custom_custom_rate"
//         ];

//         if (frm.fields_dict.items && frm.fields_dict.items.grid) {
//             fields_to_hide.forEach(field => {
//                 frm.fields_dict.items.grid.update_docfield_property(
//                     field,
//                     "hidden",
//                     1
//                 );
//             });

//             frm.refresh_field("items");
//         }
//     }
// });

// frappe.ui.form.on("Sales Invoice Item", {

//     custom_sku: function(frm, cdt, cdn) {

//         let row = locals[cdt][cdn];

//         if (!row.custom_sku) return;

//         frappe.call({
//             method: "arnav_customization.sku_mapping_backend.sku_mapper.get_sku_data",
//             args: {
//                 sku: row.custom_sku
//             },

//             callback: function(r) {

//                 if (!r.message) return;

//                 let d = r.message;

//                 frappe.model.set_value(cdt, cdn, "item_code", d.item_code);

//                 frappe.model.set_value(cdt, cdn, "qty", d.gross_weight);

//                 frappe.model.set_value(cdt, cdn, "custom_net_weight", d.net_weight);

//                 frappe.model.set_value(cdt, cdn, "custom_quantity", d.qty);

//                 setTimeout(() => {
//                     frappe.model.set_value(cdt, cdn, "rate", rate);
//                 }, 300);
                
//                 frappe.model.set_value(cdt, cdn, "gst_hsn_code", d.hsn);

//                 frappe.model.set_value(cdt, cdn, "warehouse", d.warehouse);

//                 frappe.model.set_value(cdt, cdn, "batch_no", d.batch_no);

//                 // prevents batch popup
//                 // frappe.model.set_value(cdt, cdn, "use_serial_batch_fields", 1);

//             }
//         });

//     }

// });
