frappe.ui.form.on("Opportunity", {
    refresh: function(frm) {

        if (frm.is_new()) return;

        // Sales Invoice Button
        frm.add_custom_button(__("Sales Invoice"), function () {

            frappe.new_doc("Sales Invoice", {
                customer: frm.doc.customer_name || frm.doc.title,
                opportunity: frm.doc.name,
                opportunity_title: frm.doc.title
            });

        }, __("Create"));


        // POS Button
        frm.add_custom_button(__("POS"), function () {

            frappe.model.with_doctype("POS", function () {

                let doc = frappe.model.get_new_doc("POS");

                // ===== FIELD MAPPING =====
                doc.client_name = frm.doc.customer_name || frm.doc.title || "";
                doc.email = frm.doc.contact_email || "";
                doc.opportunity = frm.doc.name;

                doc.lead_owner_1 = frm.doc.custom_lead_owner_1 || "";
                doc.lead_owner_2 = frm.doc.custom_lead_owner_2 || "";

                doc.salestype = frm.doc.custom_lead_source || "";
                doc.billtype = frm.doc.custom_metal_interest || "";

                doc.mobile_number = frm.doc.whatsapp || frm.doc.contact_mobile || frm.doc.phone || "";
                doc.pincode = frm.doc.custom_pin_code || "";
                doc.address = frm.doc.custom_address || "";

                frappe.set_route("Form", "POS", doc.name);

            });

        }, __("Create"));

    }
});
