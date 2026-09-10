frappe.listview_settings["POS"] = {
    onload(listview) {
        let applied_date_filters = [];

        const from_date = listview.page.add_field({
            fieldname: "pos_from_date",
            label: __("From Date"),
            fieldtype: "Date",
            change: apply_date_range
        });
        const to_date = listview.page.add_field({
            fieldname: "pos_to_date",
            label: __("To Date"),
            fieldtype: "Date",
            change: apply_date_range
        });

        function apply_date_range() {
            if (applied_date_filters.length && listview.filter_area.remove) {
                listview.filter_area.remove(applied_date_filters);
            }

            const from = from_date.get_value();
            const to = to_date.get_value();
            applied_date_filters = [];

            if (from) {
                applied_date_filters.push(["POS", "date", ">=", `${from} 00:00:00`]);
            }
            if (to) {
                applied_date_filters.push(["POS", "date", "<=", `${to} 23:59:59`]);
            }

            if (applied_date_filters.length) {
                listview.filter_area.add(applied_date_filters);
            } else {
                listview.refresh();
            }
        }
    }
};
