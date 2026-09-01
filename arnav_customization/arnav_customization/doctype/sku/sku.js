frappe.ui.form.on("SKU", {
    refresh(frm) {
        frm.set_df_property("breakup_info", "label", frm.doc.breakup_ref ? "Edit Breakup" : "Add Breakup");
    },

    async breakup_info(frm) {
        if (!frm.doc.breakup_ref) {
            await frm.set_value("breakup_ref", frappe.utils.get_random(12));
        }

        if (frm.is_dirty()) {
            await frm.save();
        }

        if (!arnav_customization.design_code || !arnav_customization.design_code.open_breakup_dialog) {
            frappe.throw(__("Design Code breakup controls are not loaded. Please clear cache and reload the page."));
        }

        arnav_customization.design_code.open_breakup_dialog({
            title: __("Breakup - {0}", [frm.doc.product || frm.doc.sku_code || ""]),
            sku_master: frm.doc.sku_master,
            breakup_ref: frm.doc.breakup_ref,
            on_saved(saved_breakup) {
                if (saved_breakup.breakup_ref && saved_breakup.breakup_ref !== frm.doc.breakup_ref) {
                    frm.set_value("breakup_ref", saved_breakup.breakup_ref);
                }
                frm.reload_doc();
            }
        });
    }
});
