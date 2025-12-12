frappe.views.calendar["Event Readiness"] = {
    field_map: {
        start: "event_date",
        end: "custom_event_end_date",
        title: "event_name",
        id: "name",
        allDay: 1   // 👈 force all-day events
    },
    options: {
        allDaySlot: false,  // hides time row
        eventTimeFormat: { hour: 'numeric', minute: '2-digit', meridiem: false }, // optional
        header: {
            left: "prev,next today",
            center: "title",
            right: "month,agendaWeek,agendaDay"
        }
    },
    get_events_method: "frappe.desk.calendar.get_events"
};
