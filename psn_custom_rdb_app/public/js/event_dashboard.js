frappe.pages['event-readiness-dashboard'].on_page_load = function(wrapper) {
    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Event Readiness Dashboard',
        single_column: true
    });

    // Create chart containers dynamically
    $(`
        <div class="dashboard-section">
            <h3>Event Readiness %</h3>
            <div class="readiness-chart"></div>
        </div>

        <div class="dashboard-section" style="margin-top:40px;">
            <h3>Task Status Comparison</h3>
            <div class="task-chart"></div>
        </div>
    `).appendTo(page.body);

    frappe.call({
        method: "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.get_event_dashboard_stats",
        callback: function(r) {
            const data = r.message || [];
            render_readiness_chart(page, data);
            render_task_status_chart(page, data);
        }
    });
}
