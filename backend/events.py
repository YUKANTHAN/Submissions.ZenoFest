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
        {"name": "github_url", "label": "GitHub Project URL", "type": "url", "required": True, "placeholder": "https://github.com/username/repo"},
        {"name": "abstract_link", "label": "Abstract (Google Drive DOCX Link)", "type": "url", "required": True, "placeholder": "https://drive.google.com/file/d/your-file-id/view"},
        {"name": "ppt_link", "label": "PPT (Google Drive Link)", "type": "url", "required": True, "placeholder": "https://drive.google.com/file/d/your-file-id/view"},
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
        {"name": "project_title", "label": "Project Title", "type": "text", "required": True},
        {"name": "figma_link", "label": "Figma Prototype Link", "type": "url", "required": True, "placeholder": "https://www.figma.com/proto/..."},
        {"name": "figma_file_link", "label": "Figma File Link (Editor Access)", "type": "url", "required": True, "placeholder": "https://www.figma.com/file/..."},
        {"name": "design_brief", "label": "Design Brief / Problem Statement", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "target_audience", "label": "Target Audience / Users", "type": "text", "required": True},
        {"name": "design_tools", "label": "Design Tools Used", "type": "text", "required": True, "placeholder": "Figma, FigJam, etc."},
        {"name": "user_flow", "label": "User Flow Description", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "key_screens", "label": "Key Screens Designed", "type": "textarea", "required": True, "max_length": 10000},
        {"name": "design_system", "label": "Design System / Components Used", "type": "textarea", "max_length": 5000},
        {"name": "usability_testing", "label": "Usability Testing Notes", "type": "textarea", "max_length": 5000},
        {"name": "additional_links", "label": "Additional Links", "type": "links", "required": False, "hint": "Research / References Link"},
    ],
}


def get_event_fields(event_name):
    """Return the field list for an event, or None if the event is unknown."""
    return EVENT_FIELDS.get(event_name)


def get_all_events():
    """Return a dict of {event_name: field_list} for the frontend."""
    return EVENT_FIELDS