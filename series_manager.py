import os
import json
import sys

ROSTER_FILE = "roster.json"
SERIES_ROOT = "series"

def load_json(filepath):
    if not os.path.exists(filepath):
        print(f"[ERROR] Required configuration file missing: {filepath}")
        sys.exit(1)
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_roster():
    data = load_json(ROSTER_FILE)
    faculty = data.get("faculty", [])
    if not faculty:
        print("[ERROR] No faculty personas found in roster.json!")
        sys.exit(1)
    return faculty

def resolve_lesson_and_persona(series_id="speed_math", manual_lesson_id=None):
    series_dir = os.path.join(SERIES_ROOT, series_id)
    curriculum_path = os.path.join(series_dir, "curriculum.json")
    progress_path = os.path.join(series_dir, "progress.json")

    curriculum = load_json(curriculum_path)
    progress = load_json(progress_path)
    faculty = get_roster()

    lessons = curriculum.get("lessons", [])
    if not lessons:
        print(f"[ERROR] No lessons defined in {curriculum_path}!")
        sys.exit(1)

    selected_lesson = None
    if manual_lesson_id:
        try:
            target_id = int(manual_lesson_id)
            selected_lesson = next((l for l in lessons if l["lesson_id"] == target_id), None)
            if not selected_lesson:
                print(f"[WARN] Manual lesson ID {target_id} not found. Falling back to next auto lesson.")
        except ValueError:
            pass

    if not selected_lesson:
        current_idx = progress.get("current_lesson_index", 0)
        if current_idx >= len(lessons):
            print(f"[INFO] All lessons completed for series '{series_id}'! Looping back to Lesson 1.")
            current_idx = 0
        selected_lesson = lessons[current_idx]

    lesson_id = selected_lesson["lesson_id"]
    persona_index = (lesson_id - 1) % len(faculty)
    selected_persona = faculty[persona_index]

    print(f"[SERIES] Active Series: {curriculum.get('series_title', series_id)}")
    print(f"[SERIES] Selected Lesson: #{lesson_id} - {selected_lesson.get('topic')}")
    print(f"[SERIES] Assigned Teacher: {selected_persona.get('name')} ({selected_persona.get('tagline')})")

    return {
        "series_id": series_id,
        "series_title": curriculum.get("series_title", series_id),
        "lesson": selected_lesson,
        "persona": selected_persona,
        "progress_path": progress_path,
        "curriculum_path": curriculum_path
    }

def mark_lesson_completed(series_context):
    progress_path = series_context["progress_path"]
    progress = load_json(progress_path)
    lesson_id = series_context["lesson"]["lesson_id"]

    if lesson_id not in progress.get("completed_lessons", []):
        progress.setdefault("completed_lessons", []).append(lesson_id)

    curriculum = load_json(series_context["curriculum_path"])
    total_lessons = len(curriculum.get("lessons", []))

    next_index = (progress.get("current_lesson_index", 0) + 1)
    if next_index >= total_lessons:
        next_index = 0

    progress["current_lesson_index"] = next_index
    progress["last_completed_lesson_id"] = lesson_id

    save_json(progress_path, progress)
    print(f"[SERIES] Progress saved. Next queued lesson index: {next_index}")

if __name__ == "__main__":
    ctx = resolve_lesson_and_persona("speed_math")
    print("[TEST] series_manager.py executed successfully.")
