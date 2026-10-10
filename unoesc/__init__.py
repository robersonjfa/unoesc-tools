"""
unoesc-tools — UNOESC Academic Portal + Moodle ON.

Quick start:
    import unoesc
    session = unoesc.open_session()

Or import modules:
    from unoesc import portal, moodle, grades, quiz_export
"""
from .auth   import open_session
from .portal import (
    list_disciplines,
    find_discipline,
    list_class_diaries,
    open_class_diary,
    list_meetings,
    add_meeting,
    remove_meeting,
    set_meeting_in_person,
    get_meeting_attendance,
    save_meeting_attendance,
    post_absences,
    list_teaching_plans,
    get_teaching_plan,
    list_plan_schedule,
    list_plan_units,
    list_plan_bibliographies,
    list_plan_assessments,
    analyze_plan_trail,
    plan_sections_from_plan,
    plan_activities_from_plan,
    plan_trail_sync,
    sync_trail_from_plan,
    list_grades_summary,
    list_attendance_report,
    list_a2_students,
    list_students_for_message,
    list_message_classes,
    find_message_students,
    send_message_to_students,
    send_message_to_classes,
    send_on_notification,
    notify_students,
    list_occurrences,
    report_profiles,
    report_phones,
    report_signatures,
    list_timetable,
    import_diary_grades,
    list_diary_assessments,
    extract_diary_student_map,
    post_diary_grades,
)
from .moodle import (
    open_course,
    list_sections,
    find_section,
    list_activities,
    find_activity,
    classify_section,
    get_course_structure,
    create_section,
    update_section,
    create_activity,
    update_activity,
    moodle_datetime_fields,
    get_assignment,
    get_quiz,
    get_forum,
    download_resource,
)
from .quiz_export import (
    list_category_questions,
    list_question_bank_categories,
    get_question,
    analyze_quiz,
    extract_quiz,
    extract_question_bank,
    export_quiz_docx,
    export_quiz_pdf,
    export_quiz,
    export_discipline_quiz,
    export_question_bank,
    export_discipline_question_bank,
)
from .grades import (
    list_grade_items,
    export_grades_csv,
    export_grades_excel,
    export_assignment_grades,
    export_quiz_grades,
    export_grades_for_portal,
)

__all__ = [
    # auth
    "open_session",
    # portal
    "list_disciplines", "find_discipline",
    "list_class_diaries", "open_class_diary",
    "list_meetings", "add_meeting", "remove_meeting",
    "set_meeting_in_person",
    "get_meeting_attendance", "save_meeting_attendance", "post_absences",
    "list_teaching_plans",
    "get_teaching_plan",
    "list_plan_schedule", "list_plan_units",
    "list_plan_bibliographies", "list_plan_assessments",
    "analyze_plan_trail",
    "plan_sections_from_plan", "plan_activities_from_plan",
    "plan_trail_sync", "sync_trail_from_plan",
    "list_grades_summary", "list_attendance_report", "list_a2_students",
    "list_students_for_message", "list_message_classes", "find_message_students",
    "send_message_to_students", "send_message_to_classes",
    "send_on_notification", "notify_students",
    "list_occurrences",
    "report_profiles", "report_phones", "report_signatures",
    "list_timetable",
    # moodle
    "open_course", "list_sections", "find_section",
    "list_activities", "find_activity",
    "classify_section", "get_course_structure",
    "create_section", "update_section", "create_activity", "update_activity",
    "moodle_datetime_fields",
    "get_assignment", "get_quiz", "get_forum", "download_resource",
    # grades
    "list_grade_items",
    "export_grades_csv", "export_grades_excel",
    "export_assignment_grades", "export_quiz_grades",
    "export_grades_for_portal",
    # quiz export
    "list_category_questions", "list_question_bank_categories", "get_question", "analyze_quiz",
    "extract_quiz", "extract_question_bank",
    "export_quiz_docx", "export_quiz_pdf",
    "export_quiz", "export_discipline_quiz",
    "export_question_bank", "export_discipline_question_bank",
    # portal — importação e lançamento de notas
    "list_diary_assessments",
    "import_diary_grades",
    "extract_diary_student_map",
    "post_diary_grades",
]
