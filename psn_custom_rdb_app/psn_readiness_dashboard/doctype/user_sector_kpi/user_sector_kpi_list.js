frappe.listview_settings['User Sector KPI'] = {
    onload(listview) {

        // ---------------------------
        // BUTTON 1: Sync User KPI
        // ---------------------------
        listview.page.add_menu_item(__('Sync Users & KPI'), function () {
            frappe.call({
                method: "psn_custom_rdb_app.psn_readiness_dashboard.doctype.user_sector_kpi.user_sector_kpi.sync_user_sector_kpi",
                freeze: true,
                freeze_message: __("Syncing KPI records..."),
                callback: function () {
                    frappe.msgprint("All KPI entries synced successfully!");
                    listview.refresh();
                }
            });
        });

        // ---------------------------
        // BUTTON 2: Recalculate KPI Scores (Background Job)
        // ---------------------------
        listview.page.add_menu_item(__('Recalculate KPI Scores'), function () {
            frappe.call({
                method: "psn_custom_rdb_app.psn_readiness_dashboard.doctype.user_sector_kpi.user_sector_kpi.recalculate_kpi_scores",
                freeze: true,
                freeze_message: __("Recalculating KPI scores..."),
                callback: function () {
                    frappe.msgprint("KPI score recalculation triggered as background job.");
                }
            });
        });
    }
};
