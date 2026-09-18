"""
Event-specific submission form field definitions.
Single source of truth for what each tech event's form asks.

Add a new event by appending to EVENT_FIELDS:
    "Event Name": [
        {"name": "field_key", "label": "Display Label",
         "type": "text|textarea|url|select",
         "required": True/False,
         "options": ["..."]}   # only for type="select"
    ]
"""

EVENT_FIELDS = {
    "Project Expo": [
        {"name": "project_title", "label": "Project Title", "type": "text", "required": True},
        {"name": "development_domain", "label": "Development Domain", "type": "radio", "options": ["Software", "Hardware", "Hybrid (Hardware + Software)"], "required": True},
        {"name": "problem_statement", "label": "Problem Statement", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "proposed_solution", "label": "Proposed Solution", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "technologies_used", "label": "Technologies Used", "type": "text", "required": True},
        {"name": "innovation", "label": "Innovation / Uniqueness", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "implementation", "label": "Implementation", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "target_users", "label": "Target Users", "type": "text", "required": True},
        {"name": "future_scope", "label": "Future Scope", "type": "textarea", "required": True, "max_length": 10000},
    ],
}


def get_event_fields(event_name):
    """Return the field list for an event, or None if the event is unknown."""
    return EVENT_FIELDS.get(event_name)


def get_all_events():
    """Return a dict of {event_name: field_list} for the frontend."""
    return EVENT_FIELDS