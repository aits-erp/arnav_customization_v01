frappe.ui.form.on("Opportunity", {

    refresh(frm) {

        // =========================
        // LEAD SOURCE OPTIONS
        // =========================
        update_lead_source_options(frm);

        if (frm.is_new()) return;

        // =========================
        // REMOVE OLD BUTTONS
        // =========================
        frm.remove_custom_button("POS");
        frm.remove_custom_button("Sales Invoice");

        // =========================
        // SALES INVOICE BUTTON
        // =========================
        frm.add_custom_button(__("Sales Invoice"), function () {

            frappe.new_doc("Sales Invoice", {

                customer:
                    frm.doc.customer_name ||
                    frm.doc.title ||
                    "",

                opportunity:
                    frm.doc.name || "",

                opportunity_title:
                    frm.doc.title || ""

            });

        });

        // =========================
        // POS BUTTON
        // =========================
        frm.add_custom_button(__("POS"), function () {

            console.log("loaded 1st");
            frappe.new_doc("POS", {

                client_name:
                    frm.doc.party_name ||
                    frm.doc.customer_name ||
                    frm.doc.title ||
                    "",

                email:
                    frm.doc.contact_email || "",

                opportunity:
                    frm.doc.name || "",

                lead_owner_1:
                    frm.doc.custom_lead_owner_1 || "",

                lead_owner_2:
                    frm.doc.custom_lead_owner_2 || "",

                salestype:
                    frm.doc.custom_online_lead_source ||
                    frm.doc.custom_offline_lead_source ||
                    frm.doc.custom_lead_source ||
                    "",

                billtype:
                    frm.doc.custom_metal_interest || "",

                mobile_number:
                    frm.doc.whatsapp ||
                    frm.doc.contact_mobile ||
                    frm.doc.phone ||
                    "",

                pincode:
                    frm.doc.custom_pin_code || "",

                address:
                    frm.doc.custom_address || ""

            });

        });

    },

    // =========================
    // SOURCE TYPE CHANGE
    // =========================
    custom_source_type(frm) {

        update_lead_source_options(frm);

    }

});


// =====================================
// LEAD SOURCE OPTIONS FUNCTION
// =====================================
function update_lead_source_options(frm) {

    if (!frm.doc.custom_source_type) return;

    let options = "";

    // =========================
    // OFFLINE OPTIONS
    // =========================
    if (frm.doc.custom_source_type === "Offline Source") {

        options = `Walk-in
Customer Referral
Store Referral
Existing Customer
Social Media
Exhibition
Other
Scheme`;

    }

    // =========================
    // ONLINE OPTIONS
    // =========================
    if (frm.doc.custom_source_type === "Online Source") {

        options = `Email Enquiry
Facebook DM
Google Ads
Instagram DM
Meta Ads
Online Campaign
Other
Website Organic
WhatsApp DM
YouTube Ads`;

    }

    frm.set_df_property(
        "custom_lead_source",
        "options",
        options
    );

    frm.refresh_field("custom_lead_source");

}

// frappe.ui.form.on("Opportunity", {
//     refresh: function(frm) {

//         if (frm.is_new()) return;

//         // Sales Invoice Button
//         frm.add_custom_button(__("Sales Invoice"), function () {

//             frappe.new_doc("Sales Invoice", {
//                 customer: frm.doc.customer_name || frm.doc.title,
//                 opportunity: frm.doc.name,
//                 opportunity_title: frm.doc.title
//             });

//         }, __("Create"));


//         // POS Button
//         frm.add_custom_button(__("POS"), function () {

//             frappe.model.with_doctype("POS", function () {

//                 let doc = frappe.model.get_new_doc("POS");

//                 // ===== FIELD MAPPING =====
//                 doc.client_name = frm.doc.customer_name || frm.doc.title || "";
//                 doc.email = frm.doc.contact_email || "";
//                 doc.opportunity = frm.doc.name;

//                 doc.lead_owner_1 = frm.doc.custom_lead_owner_1 || "";
//                 doc.lead_owner_2 = frm.doc.custom_lead_owner_2 || "";

//                 doc.salestype = frm.doc.custom_lead_source || "";
//                 doc.billtype = frm.doc.custom_metal_interest || "";

//                 doc.mobile_number = frm.doc.whatsapp || frm.doc.contact_mobile || frm.doc.phone || "";
//                 doc.pincode = frm.doc.custom_pin_code || "";
//                 doc.address = frm.doc.custom_address || "";

//                 frappe.set_route("Form", "POS", doc.name);

//             });

//         }, __("Create"));

//     }
// });
