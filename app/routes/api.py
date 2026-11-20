import csv
import io
import json
import math
import random
import statistics
from datetime import date, datetime, timedelta

from flask import Blueprint, Response, jsonify, request, session

from ..database import get_db
from ..models import Subject

api = Blueprint("api", __name__)


def owner_id():
    return int(session["user_id"])


def stamp():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def fail(message, status=400):
    return jsonify({"error": message}), status


def as_dict(row):
    return dict(row) if row else None


def integer(value, label, low=0, high=10000):
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{label} must be a whole number.")
    if not low <= number <= high:
        raise ValueError(f"{label} must be between {low} and {high}.")
    return number


@api.get("/tasks")
def tasks_list():
    rows = get_db().execute("""SELECT * FROM tasks WHERE user_id=?
        ORDER BY CASE status WHEN 'todo' THEN 0 ELSE 1 END, due_at""", (owner_id(),)).fetchall()
    return jsonify([dict(row) for row in rows])


@api.post("/tasks")
def task_create():
    data = request.get_json(silent=True) or {}
    title, subject = str(data.get("title", "")).strip(), str(data.get("subject", "Personal")).strip()
    if not title or not subject:
        return fail("Add a task title and subject.")
    try:
        duration = integer(data.get("duration_minutes", 45), "Duration", 5, 600)
        priority = data.get("priority", "medium")
        kind = data.get("kind", "study")
        if priority not in {"low", "medium", "high"}:
            raise ValueError("Choose low, medium or high priority.")
        if kind not in {"study", "assignment", "reading", "personal"}:
            raise ValueError("Choose a valid task type.")
        due = str(data.get("due_at", "")).strip() or None
        if due:
            datetime.fromisoformat(due)
    except ValueError as error:
        return fail(str(error))
    db = get_db()
    cursor = db.execute("""INSERT INTO tasks(user_id,title,subject,due_at,duration_minutes,priority,kind,notes,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)""", (owner_id(), title, subject, due, duration, priority, kind,
        str(data.get("notes", "")).strip()[:500], stamp()))
    db.commit()
    return jsonify(as_dict(db.execute("SELECT * FROM tasks WHERE id=?", (cursor.lastrowid,)).fetchone())), 201


@api.patch("/tasks/<int:task_id>")
def task_update(task_id):
    data = request.get_json(silent=True) or {}
    allowed = {"title", "subject", "due_at", "duration_minutes", "priority", "status", "kind", "notes"}
    fields = {key: value for key, value in data.items() if key in allowed}
    if not fields:
        return fail("There are no task changes to save.")
    if "status" in fields and fields["status"] not in {"todo", "done"}:
        return fail("Task status must be todo or done.")
    if "priority" in fields and fields["priority"] not in {"low", "medium", "high"}:
        return fail("Choose a valid priority.")
    if "duration_minutes" in fields:
        try:
            fields["duration_minutes"] = integer(fields["duration_minutes"], "Duration", 5, 600)
        except ValueError as error:
            return fail(str(error))
    if "due_at" in fields:
        fields["due_at"] = fields["due_at"] or None
        if fields["due_at"]:
            try:
                datetime.fromisoformat(fields["due_at"])
            except ValueError:
                return fail("Enter a valid due date and time.")
    if "status" in fields:
        fields["completed_at"] = stamp() if fields["status"] == "done" else None
    db = get_db()
    keys = list(fields)
    cursor = db.execute(f"UPDATE tasks SET {','.join(k + '=?' for k in keys)} WHERE id=? AND user_id=?",
                        (*[fields[k] for k in keys], task_id, owner_id()))
    db.commit()
    if cursor.rowcount == 0:
        return fail("Task not found.", 404)
    return jsonify(as_dict(db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()))


@api.delete("/tasks/<int:task_id>")
def task_delete(task_id):
    db = get_db()
    cursor = db.execute("DELETE FROM tasks WHERE id=? AND user_id=?", (task_id, owner_id()))
    db.commit()
    if cursor.rowcount == 0:
        return fail("Task not found.", 404)
    return jsonify({"ok": True})


@api.get("/courses")
def courses_list():
    rows = Subject.query.filter_by(user_id=owner_id()).order_by(Subject.name).all()
    return jsonify([{
        "id": subject.id, "name": subject.name, "color": subject.color,
        "semester": subject.category,
        "syllabus_progress": int(subject.progress[0].progress_percent) if subject.progress else 0,
    } for subject in rows])


@api.get("/exams")
def exams_list():
    rows = get_db().execute("SELECT * FROM exams WHERE user_id=? ORDER BY exam_at", (owner_id(),)).fetchall()
    return jsonify([dict(row) for row in rows])


@api.post("/exams")
def exam_create():
    data = request.get_json(silent=True) or {}
    title, subject, exam_at = (str(data.get(key, "")).strip() for key in ("title", "subject", "exam_at"))
    if not title or not subject or not exam_at:
        return fail("Add an exam title, subject and date.")
    try:
        datetime.fromisoformat(exam_at)
    except ValueError:
        return fail("Enter a valid exam date and time.")
    db = get_db()
    cursor = db.execute("""INSERT INTO exams(user_id,title,subject,exam_at,location,color,notes,created_at)
        VALUES(?,?,?,?,?,?,?,?)""", (owner_id(), title, subject, exam_at, str(data.get("location", "")).strip()[:100],
        data.get("color", "violet"), str(data.get("notes", "")).strip()[:500], stamp()))
    db.commit()
    return jsonify(as_dict(db.execute("SELECT * FROM exams WHERE id=?", (cursor.lastrowid,)).fetchone())), 201


@api.delete("/exams/<int:exam_id>")
def exam_delete(exam_id):
    db = get_db()
    cursor = db.execute("DELETE FROM exams WHERE id=? AND user_id=?", (exam_id, owner_id()))
    db.commit()
    if cursor.rowcount == 0:
        return fail("Exam not found.", 404)
    return jsonify({"ok": True})


@api.post("/sessions")
def session_create():
    data = request.get_json(silent=True) or {}
    subject = str(data.get("subject", "Study session")).strip()[:80] or "Study session"
    try:
        planned = integer(data.get("planned_minutes"), "Planned minutes", 1, 600)
        actual = integer(data.get("actual_minutes"), "Actual minutes", 0, 600)
    except ValueError as error:
        return fail(str(error))
    completed = data.get("completed", False)
    if not isinstance(completed, bool):
        return fail("Session completion must be true or false.")
    started_at = str(data.get("started_at") or stamp())
    try:
        datetime.fromisoformat(started_at)
    except ValueError:
        return fail("Enter a valid session start date and time.")
    db = get_db()
    cursor = db.execute("""INSERT INTO study_sessions(user_id,subject,planned_minutes,actual_minutes,completed,started_at,source)
        VALUES(?,?,?,?,?,?,?)""", (owner_id(), subject, planned, actual, int(completed),
        started_at, str(data.get("source", "focus"))[:30]))
    db.commit()
    return jsonify(as_dict(db.execute("SELECT * FROM study_sessions WHERE id=?", (cursor.lastrowid,)).fetchone())), 201


@api.get("/sessions")
def sessions_list():
    rows = get_db().execute(
        "SELECT * FROM study_sessions WHERE user_id=? ORDER BY started_at DESC LIMIT 500",
        (owner_id(),),
    ).fetchall()
    return jsonify([dict(row) for row in rows])


@api.delete("/sessions/<int:session_id>")
def session_delete(session_id):
    db = get_db()
    cursor = db.execute("DELETE FROM study_sessions WHERE id=? AND user_id=?", (session_id, owner_id()))
    db.commit()
    if cursor.rowcount == 0:
        return fail("Study session not found.", 404)
    return jsonify({"ok": True})


@api.post("/events")
def event_create():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()[:80]
    if not name:
        return fail("An event name is required.")
    duration = data.get("duration_ms")
    try:
        duration = integer(duration, "Interaction time", 0, 86400000) if duration is not None else None
    except ValueError as error:
        return fail(str(error))
    detail = data.get("detail", {})
    if not isinstance(detail, dict):
        return fail("Event details should be an object.")
    db = get_db()
    db.execute("INSERT INTO interaction_events(user_id,event_name,duration_ms,detail,created_at) VALUES(?,?,?,?,?)",
               (owner_id(), name, duration, json.dumps(detail)[:1500], stamp()))
    db.commit()
    return jsonify({"ok": True}), 201


@api.post("/feedback")
def feedback_create():
    data = request.get_json(silent=True) or {}
    try:
        challenge = str(data.get("primary_challenge", "")).strip()
        method = str(data.get("planning_method", "")).strip()
        if not challenge or not method:
            raise ValueError("Choose your main planning challenge and current method.")
        difficulty = integer(data.get("planning_difficulty"), "Planning difficulty", 1, 5)
        satisfaction = integer(data.get("satisfaction"), "Satisfaction", 1, 5)
        missed = integer(data.get("missed_tasks"), "Missed tasks", 0, 100)
        hours = float(data.get("current_method_hours"))
        consent = integer(data.get("consent_confirmed"), "Consent confirmation", 0, 1)
        if not 0 <= hours <= 168:
            raise ValueError("Weekly planning time must be between 0 and 168 hours.")
        if consent != 1:
            raise ValueError("Confirm that the participant agreed to share this anonymous response.")
    except (ValueError, TypeError) as error:
        return fail(str(error))
    db = get_db()
    columns = {row[1] for row in db.execute("PRAGMA table_info(survey_responses)").fetchall()}
    fields = ["user_id", "primary_challenge", "planning_method", "planning_difficulty", "satisfaction",
              "missed_tasks", "current_method_hours", "feedback", "consent_confirmed", "created_at"]
    values = [owner_id(), challenge, method, difficulty, satisfaction, missed, hours,
              str(data.get("feedback", "")).strip()[:1000], consent, stamp()]
    # Older project databases made these optional SUS columns mandatory.
    for legacy_column, default in (("sus_answers", "[]"), ("sus_score", 0)):
        if legacy_column in columns:
            fields.append(legacy_column)
            values.append(default)
    placeholders = ",".join("?" for _ in fields)
    cursor = db.execute(f"INSERT INTO survey_responses({','.join(fields)}) VALUES({placeholders})", values)
    db.commit()
    return jsonify({"id": cursor.lastrowid}), 201


@api.post("/usability-tests")
def usability_create():
    data = request.get_json(silent=True) or {}
    code = str(data.get("participant_code", "")).strip()[:40]
    if not code:
        return fail("Use a participant code such as P01. Do not enter a name.")
    try:
        baseline, prototype = float(data.get("baseline_minutes")), float(data.get("prototype_minutes"))
        if not (0 < baseline <= 600 and 0 < prototype <= 600):
            raise ValueError("Both task times must be greater than zero and at most 600 minutes.")
        baseline_success = integer(data.get("baseline_success"), "Current-method success", 0, 1)
        prototype_success = integer(data.get("prototype_success"), "Prototype success", 0, 1)
        baseline_errors = integer(data.get("baseline_errors", 0), "Current-method errors", 0, 1000)
        prototype_errors = integer(data.get("prototype_errors", 0), "Prototype errors", 0, 1000)
        satisfaction = integer(data.get("satisfaction"), "Satisfaction", 1, 5)
        consent = integer(data.get("consent_confirmed"), "Consent confirmation", 0, 1)
        if consent != 1:
            raise ValueError("Confirm that the participant agreed to take part in this test.")
        answers = [integer(answer, "SUS answer", 1, 5) for answer in data.get("sus_answers", [])]
        if len(answers) != 10:
            raise ValueError("Answer all 10 usability questions after the prototype task.")
    except (ValueError, TypeError) as error:
        return fail(str(error))
    db = get_db()
    cursor = db.execute("""INSERT INTO usability_tests(user_id,participant_code,baseline_minutes,prototype_minutes,baseline_success,
        prototype_success,baseline_errors,prototype_errors,satisfaction,sus_answers,sus_score,notes,consent_confirmed,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (owner_id(), code, baseline, prototype, baseline_success, prototype_success,
        baseline_errors, prototype_errors, satisfaction, json.dumps(answers),
        sum((value - 1) if index % 2 == 0 else (5 - value) for index, value in enumerate(answers)) * 2.5,
        str(data.get("notes", "")).strip()[:1000], consent, stamp()))
    db.commit()
    return jsonify({"id": cursor.lastrowid, "sus_score": sum((value - 1) if index % 2 == 0 else (5 - value) for index, value in enumerate(answers)) * 2.5}), 201


def paired_analysis(rows):
    baseline = [float(row["baseline_minutes"]) for row in rows]
    prototype = [float(row["prototype_minutes"]) for row in rows]
    n = len(rows)
    result = {"n": n, "mean_baseline": statistics.mean(baseline) if n else None,
              "mean_prototype": statistics.mean(prototype) if n else None,
              "mean_improvement": statistics.mean([a-b for a, b in zip(baseline, prototype)]) if n else None,
              "p_value": None, "test": None, "ci95": None, "ci_method": None,
              "effect_size": None, "effect_name": None,
              "success_baseline": sum(int(row["baseline_success"]) for row in rows)/n if n else None,
              "success_prototype": sum(int(row["prototype_success"]) for row in rows)/n if n else None,
              "mean_error_reduction": statistics.mean([int(row["baseline_errors"])-int(row["prototype_errors"]) for row in rows]) if n else None}
    if n > 1:
        differences = [a-b for a, b in zip(baseline, prototype)]
        # A percentile bootstrap interval keeps a transparent uncertainty estimate
        # available even when the rank-based test is selected.
        generator = random.Random(2026)
        bootstrap_means = sorted(statistics.mean(generator.choices(differences, k=n)) for _ in range(4000))
        result["ci95"] = [bootstrap_means[99], bootstrap_means[3899]]
        result["ci_method"] = "95% percentile bootstrap for mean time saved"
        if statistics.stdev(differences) > 0:
            try:
                from scipy import stats
                normality_ok = n >= 8 and stats.shapiro(differences).pvalue >= .05
                if normality_ok:
                    test = stats.ttest_rel(baseline, prototype, alternative="greater")
                    sem = stats.sem(differences)
                    margin = stats.t.ppf(.975, n-1) * sem
                    result.update({"p_value": float(test.pvalue), "test": "Paired t-test",
                                   "ci95": [statistics.mean(differences)-margin, statistics.mean(differences)+margin],
                                   "ci_method": "95% paired t interval",
                                   "effect_size": statistics.mean(differences)/statistics.stdev(differences),
                                   "effect_name": "Cohen's dz"})
                else:
                    test = stats.wilcoxon(baseline, prototype, alternative="greater", method="auto")
                    ranks = stats.rankdata([abs(value) for value in differences])
                    positive = sum(rank for rank, value in zip(ranks, differences) if value > 0)
                    negative = sum(rank for rank, value in zip(ranks, differences) if value < 0)
                    denominator = positive + negative
                    result.update({"p_value": float(test.pvalue), "test": "Wilcoxon signed-rank",
                                   "effect_size": (positive-negative)/denominator if denominator else 0,
                                   "effect_name": "Matched rank-biserial r"})
            except ImportError:
                result["test"] = "Install optional analysis requirements for inferential tests"
    return result


@api.get("/analytics")
def analytics():
    db = get_db()
    tasks = db.execute("SELECT status,due_at,subject FROM tasks WHERE user_id=?", (owner_id(),)).fetchall()
    sessions = db.execute("SELECT * FROM study_sessions WHERE user_id=? ORDER BY started_at DESC", (owner_id(),)).fetchall()
    events = db.execute("SELECT * FROM interaction_events WHERE user_id=? ORDER BY created_at DESC LIMIT 1500", (owner_id(),)).fetchall()
    feedback = db.execute("SELECT * FROM survey_responses WHERE user_id=? ORDER BY created_at DESC", (owner_id(),)).fetchall()
    tests = db.execute("SELECT * FROM usability_tests WHERE user_id=? ORDER BY created_at", (owner_id(),)).fetchall()
    today = date.today()
    days = []
    for offset in range(6, -1, -1):
        day = today - timedelta(days=offset)
        day_sessions = [s for s in sessions if str(s["started_at"])[:10] == day.isoformat()]
        days.append({"date": day.isoformat(), "label": day.strftime("%a"),
                     "minutes": sum(int(s["actual_minutes"]) for s in day_sessions), "sessions": len(day_sessions)})
    total_tasks = len(tasks)
    completed_tasks = sum(t["status"] == "done" for t in tasks)
    primary_challenges = {}
    for row in feedback:
        primary_challenges[row["primary_challenge"]] = primary_challenges.get(row["primary_challenge"], 0) + 1
    sus = [float(row["sus_score"]) for row in tests]
    diff = [int(row["planning_difficulty"]) for row in feedback]
    satisfaction = [int(row["satisfaction"]) for row in feedback]
    correlation = None
    if len(diff) >= 3 and len(set(diff)) > 1 and len(set(satisfaction)) > 1:
        try:
            from scipy.stats import spearmanr
            correlation = float(spearmanr(diff, satisfaction).statistic)
        except ImportError:
            correlation = None
    return jsonify({
        "tasks": {"total": total_tasks, "completed": completed_tasks,
                  "completion_rate": completed_tasks/total_tasks if total_tasks else 0},
        "sessions": {"total": len(sessions), "minutes_total": sum(int(s["actual_minutes"]) for s in sessions),
                     "minutes_today": sum(int(s["actual_minutes"]) for s in sessions if str(s["started_at"])[:10] == today.isoformat()),
                     "by_day": days, "recent": [dict(row) for row in sessions[:8]],
                     "by_subject": {subject: sum(int(s["actual_minutes"]) for s in sessions if s["subject"] == subject)
                                    for subject in sorted({s["subject"] for s in sessions})}},
        "events": {"total": len(events), "timed": sum(e["duration_ms"] is not None for e in events),
                   "names": {name: sum(e["event_name"] == name for e in events) for name in sorted({e["event_name"] for e in events})}},
        "feedback": {"n": len(feedback), "mean_difficulty": statistics.mean(diff) if diff else None,
                     "mean_satisfaction": statistics.mean(satisfaction) if satisfaction else None,
                     "difficulty_satisfaction_rho": correlation,
                     "primary_challenges": primary_challenges},
        "usability": {**paired_analysis(tests), "sus_n": len(sus), "mean_sus": statistics.mean(sus) if sus else None},
        "usability_records": [dict(row) for row in tests[-10:][::-1]],
    })


def csv_response(filename, headers, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


@api.get("/export/feedback.csv")
def export_feedback():
    rows = get_db().execute("""SELECT primary_challenge,planning_method,planning_difficulty,satisfaction,
        missed_tasks,current_method_hours,feedback,consent_confirmed,created_at FROM survey_responses WHERE user_id=? ORDER BY created_at""", (owner_id(),)).fetchall()
    return csv_response("luma-survey-responses.csv",
        ["primary_challenge", "planning_method", "difficulty_1_to_5", "satisfaction_1_to_5", "missed_tasks",
         "current_method_hours_week", "open_feedback", "consent_confirmed", "submitted_at"], [tuple(row) for row in rows])


@api.get("/export/usability.csv")
def export_usability():
    rows = get_db().execute("""SELECT participant_code,baseline_minutes,prototype_minutes,baseline_success,
        prototype_success,baseline_errors,prototype_errors,satisfaction,sus_score,consent_confirmed,created_at FROM usability_tests WHERE user_id=? ORDER BY created_at""", (owner_id(),)).fetchall()
    return csv_response("luma-usability-tests.csv",
        ["participant_code", "current_method_minutes", "prototype_minutes", "current_success", "prototype_success",
         "current_errors", "prototype_errors", "satisfaction_1_to_5", "sus_score_0_to_100", "consent_confirmed", "submitted_at"], [tuple(row) for row in rows])
