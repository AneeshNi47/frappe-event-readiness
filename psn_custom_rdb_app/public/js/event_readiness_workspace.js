frappe.pages['event-readiness-dashboard'].on_page_load = function(wrapper) {
    console.log("📌 Event Readiness Workspace JS Loaded!");

    let page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Event Readiness Dashboard',
        single_column: true
    });

    $(`
        <div id="event-kpis"></div>
        <div id="event-readiness-chart"></div>
        <div id="task-status-chart"></div>
    `).appendTo(page.body);

    frappe.call({
        method: "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.get_event_dashboard_stats",
        callback: function(r) {
            const data = r.message || [];
            console.log("📊 Data received:", data);
        }
    });
};


frappe.ready(() => {
    // Delay ensures dashboard is fully rendered
    setTimeout(() => {
        document.querySelectorAll('.dashboard-chart').forEach(chart => {
            chart.addEventListener('click', function (e) {

                // Identify clicked bar point
                const bar = e?.point || e?.dataPoint;
                if (!bar) return;

                const event_name = bar?.label || bar?.name;
                if (!event_name) return;

                // Lookup matching Event Readiness record
                frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Event Readiness",
                        filters: { event_name },
                        fieldname: "name"
                    },
                    callback(r) {
                        if (r.message?.name) {
                            // Navigate to the Event Readiness form
                            frappe.set_route("Form", "Event Readiness", r.message.name);
                        }
                    }
                });
            });
        });
    }, 1200);
});
