from datetime import date, datetime, time, timedelta, timezone

from flask import Blueprint, jsonify, request, session
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from ..extensions import db
from ..models import (
    Achievement, AITutorHistory, AnalyticsSnapshot, Note, ProgressRecord, Quiz,
    QuizAttempt, QuizQuestion, RevisionPlan, Roadmap, RoadmapTask, StudySession,
    StudyTask, Subject, User, UserProfile,
)


studyx = Blueprint("studyx_api", __name__)


def owner_id():
    return int(session["user_id"])


def now_utc():
    return datetime.now(timezone.utc)


def fail(message, status=400):
    return jsonify({"error": message}), status


def body():
    value = request.get_json(silent=True)
    return value if isinstance(value, dict) else {}


def as_iso(value):
    return value.isoformat() if value else None


def text_value(value, label, limit, required=False):
    result = str(value or "").strip()
    if required and not result:
        raise ValueError(f"{label} is required.")
    if len(result) > limit:
        raise ValueError(f"{label} must be {limit} characters or fewer.")
    return result


def owned_subject(subject_id, user_id=None):
    if subject_id in (None, ""):
        return None
    try:
        subject_id = int(subject_id)
    except (TypeError, ValueError):
        raise ValueError("Choose a valid subject.")
    subject = Subject.query.filter_by(id=subject_id, user_id=user_id or owner_id()).first()
    if not subject:
        raise ValueError("That subject does not belong to this account.")
    return subject


def profile_data(user):
    profile = user.profile
    if profile is None:
        profile = UserProfile(full_name=user.display_name)
        user.profile = profile
        db.session.flush()
    return {
        "id": user.id,
        "email": user.email,
        "full_name": profile.full_name,
        "profile_image_url": profile.profile_image_url,
        "course_name": profile.course_name,
        "preferences": profile.preferences or {},
        "created_at": user.created_at,
        "updated_at": as_iso(profile.updated_at),
    }


def subject_data(subject):
    progress = ProgressRecord.query.filter_by(user_id=subject.user_id, subject_id=subject.id).first()
    return {
        "id": subject.id, "name": subject.name, "category": subject.category, "color": subject.color,
        "progress_percent": progress.progress_percent if progress else None,
        "created_at": as_iso(subject.created_at),
    }


def note_data(note):
    return {
        "id": note.id, "subject_id": note.subject_id,
        "subject": note.subject.name if note.subject else None,
        "title": note.title, "content": note.content, "tags": note.tags or [],
        "created_at": as_iso(note.created_at), "updated_at": as_iso(note.updated_at),
    }


def roadmap_data(roadmap, include_tasks=True):
    total = len(roadmap.tasks)
    completed = sum(task.completed for task in roadmap.tasks)
    result = {
        "id": roadmap.id, "subject_id": roadmap.subject_id,
        "subject": roadmap.subject.name if roadmap.subject else None,
        "title": roadmap.title, "description": roadmap.description,
        "completed_tasks": completed, "total_tasks": total,
        "completion_percent": round((completed / total) * 100, 1) if total else 0,
        "completed": bool(total and completed == total),
        "created_at": as_iso(roadmap.created_at), "updated_at": as_iso(roadmap.updated_at),
    }
    if include_tasks:
        result["tasks"] = [{
            "id": task.id, "title": task.title, "description": task.description,
            "sort_order": task.sort_order, "completed": task.completed, "due_at": task.due_at,
            "completed_at": as_iso(task.completed_at),
        } for task in roadmap.tasks]
    return result


def quiz_data(quiz, include_questions=False):
    attempts = QuizAttempt.query.filter_by(user_id=owner_id(), quiz_id=quiz.id).all()
    result = {
        "id": quiz.id, "subject_id": quiz.subject_id,
        "subject": quiz.subject.name if quiz.subject else None,
        "title": quiz.title, "description": quiz.description,
        "question_count": len(quiz.questions), "attempt_count": len(attempts),
        "average_score": round(sum(item.percentage for item in attempts) / len(attempts), 1) if attempts else None,
        "created_at": as_iso(quiz.created_at),
    }
    if include_questions:
        # Correct answers stay on the server until an attempt is submitted.
        result["questions"] = [{
            "id": question.id, "order_index": question.order_index,
            "prompt": question.prompt, "options": question.options,
        } for question in quiz.questions]
    return result


def refresh_progress(user_id, subject_id):
    subject = Subject.query.filter_by(id=subject_id, user_id=user_id).first()
    if not subject:
        return None
    roadmaps = Roadmap.query.filter_by(user_id=user_id, subject_id=subject_id).all()
    tasks = [task for roadmap in roadmaps for task in roadmap.tasks]
    total = len(tasks)
    complete = sum(task.completed for task in tasks)
    progress = ProgressRecord.query.filter_by(user_id=user_id, subject_id=subject_id).first()
    if progress is None:
        progress = ProgressRecord(user_id=user_id, subject_id=subject_id)
        db.session.add(progress)
    progress.total_units = total
    progress.completed_units = complete
    progress.progress_percent = round(complete * 100 / total, 1) if total else 0

    if total and complete == total:
        key = f"roadmap-complete-subject-{subject_id}"
        existing = Achievement.query.filter_by(user_id=user_id, achievement_key=key).first()
        if existing is None:
            db.session.add(Achievement(
                user_id=user_id, subject_id=subject_id, achievement_key=key,
                title=f"{subject.name} roadmap complete",
                description="Completed every saved task in this learning roadmap.",
            ))
    return progress


def refresh_analytics(user_id):
    today = date.today()
    start = datetime.combine(today, time.min).isoformat()
    end = datetime.combine(today + timedelta(days=1), time.min).isoformat()
    sessions = StudySession.query.filter(
        StudySession.user_id == user_id,
        StudySession.started_at >= start,
        StudySession.started_at < end,
    ).all()
    study_minutes = sum(int(item.actual_minutes or 0) for item in sessions)
    quiz_average = db.session.query(func.avg(QuizAttempt.percentage)).filter_by(user_id=user_id).scalar()
    all_roadmaps = Roadmap.query.filter_by(user_id=user_id).all()
    roadmap_tasks = [task for roadmap in all_roadmaps for task in roadmap.tasks]
    done = sum(task.completed for task in roadmap_tasks)
    roadmap_percent = round(done * 100 / len(roadmap_tasks), 1) if roadmap_tasks else 0
    completed_tasks = StudyTask.query.filter_by(user_id=user_id, status="done").count()
    notes_count = Note.query.filter_by(user_id=user_id).count()
    snapshot = AnalyticsSnapshot.query.filter_by(user_id=user_id, snapshot_date=today).first()
    if snapshot is None:
        snapshot = AnalyticsSnapshot(user_id=user_id, snapshot_date=today)
        db.session.add(snapshot)
    snapshot.study_minutes = study_minutes
    snapshot.session_count = len(sessions)
    snapshot.completed_tasks = completed_tasks
    snapshot.average_quiz_score = float(quiz_average) if quiz_average is not None else None
    snapshot.roadmap_completion_percent = roadmap_percent
    snapshot.notes_count = notes_count
    return snapshot


@studyx.errorhandler(IntegrityError)
def database_conflict(error):
    db.session.rollback()
    return fail("That record conflicts with data already saved for this account.", 409)


@studyx.errorhandler(SQLAlchemyError)
def database_failure(error):
    db.session.rollback()
    return fail("The database could not save this request. Please try again.", 500)


@studyx.get("/profile")
def profile_get():
    user = db.session.get(User, owner_id())
    return jsonify(profile_data(user))


@studyx.patch("/profile")
def profile_update():
    data = body()
    user = db.session.get(User, owner_id())
    profile_data(user)
    profile = user.profile
    try:
        if "full_name" in data:
            name = text_value(data["full_name"], "Name", 60, required=True)
            if len(name) < 2:
                raise ValueError("Name must have at least 2 characters.")
            profile.full_name = name
            user.display_name = name
            session["display_name"] = name
        if "course_name" in data:
            profile.course_name = text_value(data["course_name"], "Course", 120)
        if "profile_image_url" in data:
            image_url = text_value(data["profile_image_url"], "Profile image URL", 500)
            if image_url and not image_url.startswith(("https://", "http://")):
                raise ValueError("Profile image URL must start with http:// or https://.")
            profile.profile_image_url = image_url
        if "preferences" in data:
            if not isinstance(data["preferences"], dict):
                raise ValueError("Preferences must be an object.")
            profile.preferences = {**(profile.preferences or {}), **data["preferences"]}
    except ValueError as error:
        db.session.rollback()
        return fail(str(error))
    db.session.commit()
    return jsonify(profile_data(user))


@studyx.get("/subjects")
def subjects_list():
    rows = Subject.query.filter_by(user_id=owner_id()).order_by(Subject.name).all()
    return jsonify([subject_data(item) for item in rows])


@studyx.post("/subjects")
def subject_create():
    data = body()
    try:
        name = text_value(data.get("name"), "Subject name", 120, required=True)
        category = text_value(data.get("category", "General"), "Category", 80) or "General"
        color = text_value(data.get("color", "mint"), "Color", 24) or "mint"
    except ValueError as error:
        return fail(str(error))
    subject = Subject(user_id=owner_id(), name=name, category=category, color=color)
    db.session.add(subject)
    db.session.flush()
    refresh_progress(owner_id(), subject.id)
    db.session.commit()
    return jsonify(subject_data(subject)), 201


@studyx.patch("/subjects/<int:subject_id>")
def subject_update(subject_id):
    subject = Subject.query.filter_by(id=subject_id, user_id=owner_id()).first()
    if not subject:
        return fail("Subject not found.", 404)
    data = body()
    try:
        for key, label, limit in (("name", "Subject name", 120), ("category", "Category", 80), ("color", "Color", 24)):
            if key in data:
                value = text_value(data[key], label, limit, required=(key == "name"))
                setattr(subject, key, value)
    except ValueError as error:
        db.session.rollback()
        return fail(str(error))
    db.session.commit()
    return jsonify(subject_data(subject))


@studyx.delete("/subjects/<int:subject_id>")
def subject_delete(subject_id):
    subject = Subject.query.filter_by(id=subject_id, user_id=owner_id()).first()
    if not subject:
        return fail("Subject not found.", 404)
    db.session.delete(subject)
    db.session.commit()
    return jsonify({"ok": True})


@studyx.get("/notes")
def notes_list():
    rows = Note.query.filter_by(user_id=owner_id()).order_by(Note.updated_at.desc()).all()
    return jsonify([note_data(item) for item in rows])


@studyx.post("/notes")
def note_create():
    data = body()
    try:
        title = text_value(data.get("title"), "Note title", 180, required=True)
        content = text_value(data.get("content"), "Note content", 50000)
        subject = owned_subject(data.get("subject_id"))
        tags = data.get("tags", [])
        if not isinstance(tags, list) or len(tags) > 15:
            raise ValueError("Add at most 15 note tags.")
        tags = [text_value(tag, "Tag", 32, required=True) for tag in tags]
    except ValueError as error:
        return fail(str(error))
    note = Note(user_id=owner_id(), subject=subject, title=title, content=content, tags=tags)
    db.session.add(note)
    db.session.commit()
    return jsonify(note_data(note)), 201


@studyx.patch("/notes/<int:note_id>")
def note_update(note_id):
    note = Note.query.filter_by(id=note_id, user_id=owner_id()).first()
    if not note:
        return fail("Note not found.", 404)
    data = body()
    try:
        if "title" in data:
            note.title = text_value(data["title"], "Note title", 180, required=True)
        if "content" in data:
            note.content = text_value(data["content"], "Note content", 50000)
        if "subject_id" in data:
            note.subject = owned_subject(data["subject_id"])
        if "tags" in data:
            if not isinstance(data["tags"], list) or len(data["tags"]) > 15:
                raise ValueError("Add at most 15 note tags.")
            note.tags = [text_value(tag, "Tag", 32, required=True) for tag in data["tags"]]
    except ValueError as error:
        db.session.rollback()
        return fail(str(error))
    db.session.commit()
    return jsonify(note_data(note))


@studyx.delete("/notes/<int:note_id>")
def note_delete(note_id):
    note = Note.query.filter_by(id=note_id, user_id=owner_id()).first()
    if not note:
        return fail("Note not found.", 404)
    db.session.delete(note)
    db.session.commit()
    return jsonify({"ok": True})


def normalize_questions(raw_questions):
    if not isinstance(raw_questions, list) or not 1 <= len(raw_questions) <= 50:
        raise ValueError("A quiz needs between 1 and 50 questions.")
    result = []
    for order, raw in enumerate(raw_questions):
        if not isinstance(raw, dict):
            raise ValueError(f"Question {order + 1} is invalid.")
        prompt = text_value(raw.get("prompt"), f"Question {order + 1}", 1500, required=True)
        options = raw.get("options")
        if not isinstance(options, list) or not 2 <= len(options) <= 8:
            raise ValueError(f"Question {order + 1} needs between 2 and 8 options.")
        options = [text_value(option, "Answer option", 300, required=True) for option in options]
        correct = raw.get("correct_answer")
        if isinstance(correct, int) and not isinstance(correct, bool) and 0 <= correct < len(options):
            correct = options[correct]
        else:
            correct = str(correct or "").strip()
        if correct not in options:
            raise ValueError(f"Choose one of the listed options as the answer to question {order + 1}.")
        result.append({
            "order_index": order, "prompt": prompt, "options": options,
            "correct_answer": correct, "explanation": text_value(raw.get("explanation"), "Explanation", 2000),
        })
    return result


@studyx.get("/quizzes")
def quizzes_list():
    rows = Quiz.query.filter_by(user_id=owner_id()).order_by(Quiz.created_at.desc()).all()
    return jsonify([quiz_data(item) for item in rows])


@studyx.post("/quizzes")
def quiz_create():
    data = body()
    try:
        title = text_value(data.get("title"), "Quiz title", 180, required=True)
        description = text_value(data.get("description"), "Description", 3000)
        subject = owned_subject(data.get("subject_id"))
        questions = normalize_questions(data.get("questions"))
    except ValueError as error:
        return fail(str(error))
    quiz = Quiz(user_id=owner_id(), subject=subject, title=title, description=description)
    quiz.questions = [QuizQuestion(**question) for question in questions]
    db.session.add(quiz)
    db.session.commit()
    return jsonify(quiz_data(quiz, include_questions=True)), 201


@studyx.get("/quizzes/<int:quiz_id>")
def quiz_get(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=owner_id()).first()
    if not quiz:
        return fail("Quiz not found.", 404)
    return jsonify(quiz_data(quiz, include_questions=True))


@studyx.patch("/quizzes/<int:quiz_id>")
def quiz_update(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=owner_id()).first()
    if not quiz:
        return fail("Quiz not found.", 404)
    data = body()
    try:
        if "title" in data:
            quiz.title = text_value(data["title"], "Quiz title", 180, required=True)
        if "description" in data:
            quiz.description = text_value(data["description"], "Description", 3000)
        if "subject_id" in data:
            quiz.subject = owned_subject(data["subject_id"])
        if "questions" in data:
            if quiz.attempts:
                raise ValueError("Questions cannot be edited after students have attempted this quiz.")
            questions = normalize_questions(data["questions"])
            quiz.questions = [QuizQuestion(**question) for question in questions]
    except ValueError as error:
        db.session.rollback()
        return fail(str(error))
    db.session.commit()
    return jsonify(quiz_data(quiz, include_questions=True))


@studyx.delete("/quizzes/<int:quiz_id>")
def quiz_delete(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=owner_id()).first()
    if not quiz:
        return fail("Quiz not found.", 404)
    db.session.delete(quiz)
    db.session.commit()
    return jsonify({"ok": True})


@studyx.get("/quizzes/<int:quiz_id>/attempts")
def quiz_attempts_list(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=owner_id()).first()
    if not quiz:
        return fail("Quiz not found.", 404)
    attempts = QuizAttempt.query.filter_by(user_id=owner_id(), quiz_id=quiz.id).order_by(QuizAttempt.attempted_at.desc()).all()
    return jsonify([{
        "id": item.id, "score": item.score, "total_questions": item.total_questions,
        "percentage": item.percentage, "answers": item.answers, "attempted_at": as_iso(item.attempted_at),
    } for item in attempts])


@studyx.post("/quizzes/<int:quiz_id>/attempts")
def quiz_attempt_create(quiz_id):
    quiz = Quiz.query.filter_by(id=quiz_id, user_id=owner_id()).first()
    if not quiz:
        return fail("Quiz not found.", 404)
    if not quiz.questions:
        return fail("This quiz has no questions.", 409)
    answers = body().get("answers")
    if isinstance(answers, list):
        answers = {str(question.id): value for question, value in zip(quiz.questions, answers)}
    if not isinstance(answers, dict):
        return fail("Submit answers as an object keyed by question ID.")
    expected_ids = {question.id for question in quiz.questions}
    normalized = {}
    score = 0
    for question in quiz.questions:
        submitted = answers.get(str(question.id), answers.get(question.id))
        if submitted is None:
            return fail("Answer every question before submitting.")
        submitted = str(submitted).strip()
        if submitted not in question.options:
            return fail("Each answer must match one of that question's options.")
        normalized[str(question.id)] = submitted
        score += submitted == question.correct_answer
    if set(str(key) for key in answers) - {str(key) for key in expected_ids}:
        return fail("The submission contains a question that is not part of this quiz.")
    attempt = QuizAttempt(
        user_id=owner_id(), quiz_id=quiz.id, score=score,
        total_questions=len(quiz.questions), percentage=round(score * 100 / len(quiz.questions), 1),
        answers=normalized,
    )
    db.session.add(attempt)
    if attempt.percentage == 100:
        key = f"quiz-perfect-{quiz.id}"
        if not Achievement.query.filter_by(user_id=owner_id(), achievement_key=key).first():
            db.session.add(Achievement(
                user_id=owner_id(), subject_id=quiz.subject_id, achievement_key=key,
                title=f"Perfect score: {quiz.title}",
                description="Answered every question correctly on a saved quiz attempt.",
            ))
    db.session.commit()
    return jsonify({
        "id": attempt.id, "score": attempt.score, "total_questions": attempt.total_questions,
        "percentage": attempt.percentage, "answers": normalized,
        "review": {str(item.id): {"correct_answer": item.correct_answer, "explanation": item.explanation}
                   for item in quiz.questions},
        "attempted_at": as_iso(attempt.attempted_at),
    }), 201


@studyx.get("/roadmaps")
def roadmaps_list():
    rows = Roadmap.query.filter_by(user_id=owner_id()).order_by(Roadmap.created_at.desc()).all()
    return jsonify([roadmap_data(item) for item in rows])


@studyx.post("/roadmaps")
def roadmap_create():
    data = body()
    try:
        title = text_value(data.get("title"), "Roadmap title", 180, required=True)
        description = text_value(data.get("description"), "Description", 3000)
        subject = owned_subject(data.get("subject_id"))
        raw_tasks = data.get("tasks")
        if not isinstance(raw_tasks, list) or not 1 <= len(raw_tasks) <= 100:
            raise ValueError("A roadmap needs between 1 and 100 tasks.")
        tasks = []
        for index, item in enumerate(raw_tasks):
            if isinstance(item, str):
                item = {"title": item}
            if not isinstance(item, dict):
                raise ValueError(f"Roadmap task {index + 1} is invalid.")
            due_at = text_value(item.get("due_at"), "Due date", 40) or None
            if due_at:
                datetime.fromisoformat(due_at)
            tasks.append(RoadmapTask(
                title=text_value(item.get("title"), f"Task {index + 1}", 180, required=True),
                description=text_value(item.get("description"), "Task description", 1500),
                sort_order=index, due_at=due_at,
            ))
    except (ValueError, TypeError) as error:
        return fail(str(error))
    roadmap = Roadmap(user_id=owner_id(), subject=subject, title=title,
                      description=description, tasks=tasks)
    db.session.add(roadmap)
    db.session.flush()
    if subject:
        refresh_progress(owner_id(), subject.id)
    db.session.commit()
    return jsonify(roadmap_data(roadmap)), 201


@studyx.patch("/roadmaps/<int:roadmap_id>")
def roadmap_update(roadmap_id):
    roadmap = Roadmap.query.filter_by(id=roadmap_id, user_id=owner_id()).first()
    if not roadmap:
        return fail("Roadmap not found.", 404)
    data = body()
    old_subject_id = roadmap.subject_id
    try:
        if "title" in data:
            roadmap.title = text_value(data["title"], "Roadmap title", 180, required=True)
        if "description" in data:
            roadmap.description = text_value(data["description"], "Description", 3000)
        if "subject_id" in data:
            roadmap.subject = owned_subject(data["subject_id"])
    except ValueError as error:
        db.session.rollback()
        return fail(str(error))
    db.session.flush()
    if old_subject_id:
        refresh_progress(owner_id(), old_subject_id)
    if roadmap.subject_id:
        refresh_progress(owner_id(), roadmap.subject_id)
    db.session.commit()
    return jsonify(roadmap_data(roadmap))


@studyx.delete("/roadmaps/<int:roadmap_id>")
def roadmap_delete(roadmap_id):
    roadmap = Roadmap.query.filter_by(id=roadmap_id, user_id=owner_id()).first()
    if not roadmap:
        return fail("Roadmap not found.", 404)
    subject_id = roadmap.subject_id
    db.session.delete(roadmap)
    db.session.flush()
    if subject_id:
        refresh_progress(owner_id(), subject_id)
    db.session.commit()
    return jsonify({"ok": True})


@studyx.post("/roadmaps/<int:roadmap_id>/tasks")
def roadmap_task_create(roadmap_id):
    roadmap = Roadmap.query.filter_by(id=roadmap_id, user_id=owner_id()).first()
    if not roadmap:
        return fail("Roadmap not found.", 404)
    data = body()
    try:
        title = text_value(data.get("title"), "Task title", 180, required=True)
        description = text_value(data.get("description"), "Task description", 1500)
        due_at = text_value(data.get("due_at"), "Due date", 40) or None
    except ValueError as error:
        return fail(str(error))
    task = RoadmapTask(roadmap_id=roadmap.id, title=title, description=description,
                       due_at=due_at, sort_order=len(roadmap.tasks))
    db.session.add(task)
    db.session.flush()
    if roadmap.subject_id:
        refresh_progress(owner_id(), roadmap.subject_id)
    db.session.commit()
    return jsonify(roadmap_data(roadmap)), 201


@studyx.patch("/roadmaps/<int:roadmap_id>/tasks/<int:task_id>")
def roadmap_task_update(roadmap_id, task_id):
    roadmap = Roadmap.query.filter_by(id=roadmap_id, user_id=owner_id()).first()
    task = RoadmapTask.query.filter_by(id=task_id, roadmap_id=roadmap_id).first() if roadmap else None
    if not roadmap or not task:
        return fail("Roadmap task not found.", 404)
    data = body()
    try:
        if "title" in data:
            task.title = text_value(data["title"], "Task title", 180, required=True)
        if "description" in data:
            task.description = text_value(data["description"], "Task description", 1500)
        if "due_at" in data:
            task.due_at = text_value(data["due_at"], "Due date", 40) or None
            if task.due_at:
                datetime.fromisoformat(task.due_at)
        if "completed" in data:
            if not isinstance(data["completed"], bool):
                raise ValueError("Task completion must be true or false.")
            task.completed = data["completed"]
            task.completed_at = now_utc() if task.completed else None
    except ValueError as error:
        db.session.rollback()
        return fail(str(error))
    db.session.flush()
    if roadmap.subject_id:
        refresh_progress(owner_id(), roadmap.subject_id)
    db.session.commit()
    return jsonify(roadmap_data(roadmap))


@studyx.delete("/roadmaps/<int:roadmap_id>/tasks/<int:task_id>")
def roadmap_task_delete(roadmap_id, task_id):
    roadmap = Roadmap.query.filter_by(id=roadmap_id, user_id=owner_id()).first()
    task = RoadmapTask.query.filter_by(id=task_id, roadmap_id=roadmap_id).first() if roadmap else None
    if not roadmap or not task:
        return fail("Roadmap task not found.", 404)
    subject_id = roadmap.subject_id
    db.session.delete(task)
    roadmap.tasks.remove(task)
    db.session.flush()
    if subject_id:
        refresh_progress(owner_id(), subject_id)
    db.session.commit()
    return jsonify(roadmap_data(roadmap))


@studyx.get("/progress")
def progress_get():
    user_id = owner_id()
    subjects = Subject.query.filter_by(user_id=user_id).all()
    for subject in subjects:
        refresh_progress(user_id, subject.id)
    db.session.commit()
    progress_rows = ProgressRecord.query.filter_by(user_id=user_id).all()
    achievements = Achievement.query.filter_by(user_id=user_id).order_by(Achievement.earned_at.desc()).all()
    return jsonify({
        "subjects": [{
            "subject_id": item.subject_id, "subject": item.subject.name,
            "completed_units": item.completed_units, "total_units": item.total_units,
            "progress_percent": item.progress_percent, "updated_at": as_iso(item.updated_at),
        } for item in progress_rows],
        "achievements": [{
            "id": item.id, "subject_id": item.subject_id, "key": item.achievement_key,
            "title": item.title, "description": item.description, "earned_at": as_iso(item.earned_at),
        } for item in achievements],
    })


@studyx.get("/tutor-history")
def tutor_history_list():
    rows = AITutorHistory.query.filter_by(user_id=owner_id()).order_by(AITutorHistory.created_at.desc()).limit(100).all()
    return jsonify([{
        "id": item.id, "subject_id": item.subject_id, "question": item.question,
        "response": item.response, "provider": item.provider, "model_name": item.model_name,
        "created_at": as_iso(item.created_at),
    } for item in rows])


@studyx.post("/tutor-history")
def tutor_history_create():
    data = body()
    try:
        question = text_value(data.get("question"), "Question", 5000, required=True)
        response = text_value(data.get("response"), "Tutor response", 20000, required=True)
        subject = owned_subject(data.get("subject_id"))
        provider = text_value(data.get("provider", "manual"), "Provider", 80) or "manual"
        model_name = text_value(data.get("model_name"), "Model name", 120)
    except ValueError as error:
        return fail(str(error))
    item = AITutorHistory(user_id=owner_id(), subject_id=subject.id if subject else None,
                          question=question, response=response, provider=provider, model_name=model_name)
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id, "question": item.question, "response": item.response,
                    "subject_id": item.subject_id, "provider": item.provider,
                    "model_name": item.model_name, "created_at": as_iso(item.created_at)}), 201


@studyx.patch("/tutor-history/<int:item_id>")
def tutor_history_update(item_id):
    item = AITutorHistory.query.filter_by(id=item_id, user_id=owner_id()).first()
    if not item:
        return fail("Tutor history item not found.", 404)
    data = body()
    try:
        if "question" in data:
            item.question = text_value(data["question"], "Question", 5000, required=True)
        if "response" in data:
            item.response = text_value(data["response"], "Tutor response", 20000, required=True)
        if "provider" in data:
            item.provider = text_value(data["provider"], "Provider", 80, required=True)
        if "model_name" in data:
            item.model_name = text_value(data["model_name"], "Model name", 120)
        if "subject_id" in data:
            subject = owned_subject(data["subject_id"])
            item.subject_id = subject.id if subject else None
    except ValueError as error:
        db.session.rollback()
        return fail(str(error))
    db.session.commit()
    return jsonify({
        "id": item.id, "subject_id": item.subject_id, "question": item.question,
        "response": item.response, "provider": item.provider, "model_name": item.model_name,
        "created_at": as_iso(item.created_at),
    })


@studyx.delete("/tutor-history/<int:item_id>")
def tutor_history_delete(item_id):
    item = AITutorHistory.query.filter_by(id=item_id, user_id=owner_id()).first()
    if not item:
        return fail("Tutor history item not found.", 404)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


@studyx.get("/revision-planner")
def revisions_list():
    rows = RevisionPlan.query.filter_by(user_id=owner_id()).order_by(RevisionPlan.due_at).all()
    return jsonify([{
        "id": item.id, "subject_id": item.subject_id, "note_id": item.note_id,
        "title": item.title, "due_at": item.due_at, "interval_days": item.interval_days,
        "status": item.status, "completed_at": as_iso(item.completed_at),
        "created_at": as_iso(item.created_at),
    } for item in rows])


@studyx.post("/revision-planner")
def revision_create():
    data = body()
    try:
        title = text_value(data.get("title"), "Revision title", 180, required=True)
        due_at = text_value(data.get("due_at"), "Due date", 40, required=True)
        datetime.fromisoformat(due_at)
        interval_days = int(data.get("interval_days", 1))
        if not 1 <= interval_days <= 365:
            raise ValueError("Revision interval must be between 1 and 365 days.")
        subject = owned_subject(data.get("subject_id"))
        note_id = data.get("note_id")
        if note_id not in (None, ""):
            note = Note.query.filter_by(id=int(note_id), user_id=owner_id()).first()
            if not note:
                raise ValueError("Choose a note saved to this account.")
            note_id = note.id
        else:
            note_id = None
    except (ValueError, TypeError) as error:
        return fail(str(error))
    item = RevisionPlan(user_id=owner_id(), subject_id=subject.id if subject else None,
                        note_id=note_id, title=title, due_at=due_at, interval_days=interval_days)
    db.session.add(item)
    db.session.commit()
    return jsonify({"id": item.id, "subject_id": item.subject_id, "note_id": item.note_id,
                    "title": item.title, "due_at": item.due_at, "interval_days": item.interval_days,
                    "status": item.status, "created_at": as_iso(item.created_at)}), 201


@studyx.patch("/revision-planner/<int:item_id>")
def revision_update(item_id):
    item = RevisionPlan.query.filter_by(id=item_id, user_id=owner_id()).first()
    if not item:
        return fail("Revision item not found.", 404)
    data = body()
    try:
        if "title" in data:
            item.title = text_value(data["title"], "Revision title", 180, required=True)
        if "due_at" in data:
            item.due_at = text_value(data["due_at"], "Due date", 40, required=True)
            datetime.fromisoformat(item.due_at)
        if "interval_days" in data:
            item.interval_days = int(data["interval_days"])
            if not 1 <= item.interval_days <= 365:
                raise ValueError("Revision interval must be between 1 and 365 days.")
        if "subject_id" in data:
            subject = owned_subject(data["subject_id"])
            item.subject_id = subject.id if subject else None
        if "note_id" in data:
            if data["note_id"] in (None, ""):
                item.note_id = None
            else:
                note = Note.query.filter_by(id=int(data["note_id"]), user_id=owner_id()).first()
                if not note:
                    raise ValueError("Choose a note saved to this account.")
                item.note_id = note.id
        if "status" in data:
            if data["status"] not in {"scheduled", "completed", "skipped"}:
                raise ValueError("Choose scheduled, completed or skipped.")
            item.status = data["status"]
            item.completed_at = now_utc() if item.status == "completed" else None
    except (ValueError, TypeError) as error:
        db.session.rollback()
        return fail(str(error))
    db.session.commit()
    return jsonify({"id": item.id, "subject_id": item.subject_id, "note_id": item.note_id,
                    "title": item.title, "due_at": item.due_at, "interval_days": item.interval_days,
                    "status": item.status, "completed_at": as_iso(item.completed_at),
                    "created_at": as_iso(item.created_at)})


@studyx.delete("/revision-planner/<int:item_id>")
def revision_delete(item_id):
    item = RevisionPlan.query.filter_by(id=item_id, user_id=owner_id()).first()
    if not item:
        return fail("Revision item not found.", 404)
    db.session.delete(item)
    db.session.commit()
    return jsonify({"ok": True})


@studyx.get("/dashboard")
def dashboard_summary():
    user_id = owner_id()
    user = db.session.get(User, user_id)
    profile = profile_data(user)
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    sessions = StudySession.query.filter_by(user_id=user_id).all()
    all_minutes = sum(int(item.actual_minutes or 0) for item in sessions)
    week_minutes = sum(
        int(item.actual_minutes or 0) for item in sessions
        if str(item.started_at)[:10] >= week_start.isoformat()
    )
    attempts = QuizAttempt.query.filter_by(user_id=user_id).all()
    quiz_average = round(sum(item.percentage for item in attempts) / len(attempts), 1) if attempts else None
    quiz_latest = max(attempts, key=lambda item: item.attempted_at) if attempts else None
    roadmaps = Roadmap.query.filter_by(user_id=user_id).all()
    all_roadmap_tasks = [task for roadmap in roadmaps for task in roadmap.tasks]
    roadmap_done = sum(task.completed for task in all_roadmap_tasks)
    roadmap_percent = round(roadmap_done * 100 / len(all_roadmap_tasks), 1) if all_roadmap_tasks else None
    for subject in Subject.query.filter_by(user_id=user_id).all():
        refresh_progress(user_id, subject.id)
    progress_rows = ProgressRecord.query.filter_by(user_id=user_id).all()
    tracked_progress = [item for item in progress_rows if item.total_units > 0]
    snapshot = refresh_analytics(user_id)
    db.session.commit()
    return jsonify({
        "profile": profile,
        "study": {
            "total_minutes": all_minutes, "total_hours": round(all_minutes / 60, 1),
            "week_minutes": week_minutes, "session_count": len(sessions),
        },
        "quizzes": {
            "attempt_count": len(attempts), "average_score": quiz_average,
            "latest_score": quiz_latest.percentage if quiz_latest else None,
        },
        "roadmaps": {
            "count": len(roadmaps), "completed_count": sum(bool(item.tasks) and all(task.completed for task in item.tasks) for item in roadmaps),
            "completed_tasks": roadmap_done, "total_tasks": len(all_roadmap_tasks),
            "completion_percent": roadmap_percent,
        },
        "progress": {
            "subjects": len(progress_rows),
            "average_percent": round(sum(item.progress_percent for item in tracked_progress) / len(tracked_progress), 1) if tracked_progress else None,
        },
        "analytics": {
            "snapshot_date": snapshot.snapshot_date.isoformat(),
            "study_minutes": snapshot.study_minutes, "session_count": snapshot.session_count,
            "completed_tasks": snapshot.completed_tasks, "average_quiz_score": snapshot.average_quiz_score,
            "roadmap_completion_percent": snapshot.roadmap_completion_percent,
            "notes_count": snapshot.notes_count, "generated_at": as_iso(snapshot.generated_at),
        },
    })


@studyx.get("/analytics")
def analytics_history():
    snapshot = refresh_analytics(owner_id())
    db.session.commit()
    rows = AnalyticsSnapshot.query.filter_by(user_id=owner_id()).order_by(
        AnalyticsSnapshot.snapshot_date.desc()
    ).limit(90).all()
    return jsonify([{
        "snapshot_date": item.snapshot_date.isoformat(), "study_minutes": item.study_minutes,
        "session_count": item.session_count, "completed_tasks": item.completed_tasks,
        "average_quiz_score": item.average_quiz_score,
        "roadmap_completion_percent": item.roadmap_completion_percent,
        "notes_count": item.notes_count, "generated_at": as_iso(item.generated_at),
    } for item in rows])
