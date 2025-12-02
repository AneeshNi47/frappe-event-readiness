frappe.pages['event-readiness-dash'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Event Readiness Dashboard',
		single_column: true
	});
}

frappe.ready(() => {
    setTimeout(() => {
        document.querySelectorAll('.chart-wrapper').forEach(chartEl => {
            chartEl.addEventListener('click', e => {
                const point = e?.point || e?.dataPoint;
                if (!point) return;

                const label = point.label || point.name;
                if (!label) return;

                frappe.call({
                    method: "frappe.client.get_value",
                    args: {
                        doctype: "Event Readiness",
                        filters: { event_name: label },
                        fieldname: "name"
                    },
                    callback: r => {
                        if (r.message?.name) {
                            frappe.set_route("Form", "Event Readiness", r.message.name);
                        } else {
                            frappe.msgprint("Event not found: " + label);
                        }
                    }
                });
            });
        });
    }, 1500);
});
