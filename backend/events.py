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
        {"name": "submission_method", "label": "How will you submit the PPT and Abstract?", "type": "radio", "options": ["Email", "Google Drive Link"], "required": True},
        {"name": "project_title", "label": "Project Title", "type": "text", "required": True},
        {"name": "github_url", "label": "GitHub Project URL (Optional)", "type": "url", "required": False, "placeholder": "https://github.com/username/repo"},
        {"name": "abstract_link", "label": "Abstract (Google Drive DOCX Link)", "type": "url", "required": False, "placeholder": "https://drive.google.com/file/d/your-file-id/view", "depends_on": {"field": "submission_method", "value": "Google Drive Link"}},
        {"name": "ppt_link", "label": "PPT (Google Drive Link)", "type": "url", "required": False, "placeholder": "https://drive.google.com/file/d/your-file-id/view", "depends_on": {"field": "submission_method", "value": "Google Drive Link"}},
        {"name": "mail_instructions", "label": "", "type": "mail_template", "required": False},
        {"name": "development_domain", "label": "Development Domain", "type": "radio", "options": ["Software", "Hardware", "Hybrid (Hardware + Software)"], "required": True},
        {"name": "problem_statement", "label": "Problem Statement", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "proposed_solution", "label": "Proposed Solution", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "technologies_used", "label": "Technologies Used", "type": "text", "required": True},
        {"name": "innovation", "label": "Innovation / Uniqueness", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "implementation", "label": "Implementation", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "target_users", "label": "Target Users", "type": "text", "required": True},
        {"name": "future_scope", "label": "Future Scope", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "additional_links", "label": "Additional Links", "type": "links", "required": False, "hint": "UI/UX Design Link"},
    ],
    "UI/UX Design using Figma": [
        {"name": "problem_statement", "label": "Problem Statement", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "project_title", "label": "Project Title", "type": "text", "required": True},
        {"name": "short_description", "label": "Short Project Description", "type": "textarea", "required": True, "max_length": 5000},
        {"name": "figma_link", "label": "Figma Prototype Link", "type": "url", "required": True, "placeholder": "https://www.figma.com/proto/..."},
    ],
}


def get_event_fields(event_name):
    """Return the field list for an event, or None if the event is unknown."""
    return EVENT_FIELDS.get(event_name)


def get_all_events():
    """Return a dict of {event_name: field_list} for the frontend."""
    return EVENT_FIELDS