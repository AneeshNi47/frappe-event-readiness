frappe.query_reports["Event Readiness Progress Chart Source"] = {
    filters: [],

    get_chart_data: function() {
        return frappe.call({
            method: "psn_custom_rdb_app.psn_readiness_dashboard.event_logic.get_event_progress"
        }).then(r => {
            const data = r.message || [];
            return {
                labels: data.map(d => d.event_name),
                datasets: [
                    {
                        name: "Readinessssds %",
                        values: data.map(d => d.progress)
                    }
                ],
                type: "bar"
            };
        });
    }
};
