from datetime import datetime, timezone

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    display_name = db.Column(db.String(60), nullable=False)
    email = db.Column(db.String(160), nullable=False, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.String(40), nullable=False)

    profile = db.relationship("UserProfile", back_populates="user", uselist=False,
                              cascade="all, delete-orphan")
    subjects = db.relationship("Subject", back_populates="user", cascade="all, delete-orphan")
    notes = db.relationship("Note", back_populates="user", cascade="all, delete-orphan")
    quizzes = db.relationship("Quiz", back_populates="user", cascade="all, delete-orphan")
    roadmaps = db.relationship("Roadmap", back_populates="user", cascade="all, delete-orphan")


class UserProfile(db.Model):
    __tablename__ = "user_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    profile_image_url = db.Column(db.String(500), nullable=False, default="")
    course_name = db.Column(db.String(120), nullable=False, default="")
    preferences = db.Column(db.JSON, nullable=False, default=dict)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="profile")


class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    color = db.Column(db.String(24), nullable=False, default="mint")
    semester = db.Column(db.String(80), nullable=False, default="")
    syllabus_progress = db.Column(db.Integer, nullable=False, default=0)


class Subject(db.Model):
    __tablename__ = "subjects"
    __table_args__ = (db.UniqueConstraint("user_id", "name", name="uq_subject_user_name"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(80), nullable=False, default="General")
    color = db.Column(db.String(24), nullable=False, default="mint")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="subjects")
    notes = db.relationship("Note", back_populates="subject")
    quizzes = db.relationship("Quiz", back_populates="subject")
    roadmaps = db.relationship("Roadmap", back_populates="subject")
    progress = db.relationship("ProgressRecord", back_populates="subject",
                              cascade="all, delete-orphan", passive_deletes=True)


class StudyTask(db.Model):
    __tablename__ = "tasks"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    subject = db.Column(db.String(120), nullable=False, default="Personal")
    due_at = db.Column(db.String(40))
    duration_minutes = db.Column(db.Integer, nullable=False, default=45)
    priority = db.Column(db.String(16), nullable=False, default="medium")
    status = db.Column(db.String(16), nullable=False, default="todo")
    kind = db.Column(db.String(24), nullable=False, default="study")
    notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.String(40), nullable=False)
    completed_at = db.Column(db.String(40))


class Exam(db.Model):
    __tablename__ = "exams"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = db.Column(db.String(160), nullable=False)
    subject = db.Column(db.String(120), nullable=False)
    exam_at = db.Column(db.String(40), nullable=False)
    location = db.Column(db.String(120), nullable=False, default="")
    color = db.Column(db.String(24), nullable=False, default="violet")
    notes = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.String(40), nullable=False)


class StudySession(db.Model):
    __tablename__ = "study_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    subject = db.Column(db.String(120), nullable=False)
    planned_minutes = db.Column(db.Integer, nullable=False)
    actual_minutes = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    started_at = db.Column(db.String(40), nullable=False)
    source = db.Column(db.String(30), nullable=False, default="focus")


class InteractionEvent(db.Model):
    __tablename__ = "interaction_events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_name = db.Column(db.String(80), nullable=False)
    duration_ms = db.Column(db.Integer)
    detail = db.Column(db.Text, nullable=False, default="{}")
    created_at = db.Column(db.String(40), nullable=False)


class SurveyResponse(db.Model):
    __tablename__ = "survey_responses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    primary_challenge = db.Column(db.String(120), nullable=False)
    planning_method = db.Column(db.String(120), nullable=False)
    planning_difficulty = db.Column(db.Integer, nullable=False)
    satisfaction = db.Column(db.Integer, nullable=False)
    missed_tasks = db.Column(db.Integer, nullable=False, default=0)
    current_method_hours = db.Column(db.Float, nullable=False, default=0)
    feedback = db.Column(db.Text, nullable=False, default="")
    sus_answers = db.Column(db.JSON, nullable=False, default=list)
    sus_score = db.Column(db.Float, nullable=False, default=0)
    consent_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.String(40), nullable=False)


class UsabilityTest(db.Model):
    __tablename__ = "usability_tests"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    participant_code = db.Column(db.String(40), nullable=False)
    baseline_minutes = db.Column(db.Float, nullable=False)
    prototype_minutes = db.Column(db.Float, nullable=False)
    baseline_success = db.Column(db.Boolean, nullable=False)
    prototype_success = db.Column(db.Boolean, nullable=False)
    baseline_errors = db.Column(db.Integer, nullable=False, default=0)
    prototype_errors = db.Column(db.Integer, nullable=False, default=0)
    satisfaction = db.Column(db.Integer, nullable=False)
    sus_answers = db.Column(db.JSON, nullable=False, default=list)
    sus_score = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=False, default="")
    consent_confirmed = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.String(40), nullable=False)


class Note(db.Model):
    __tablename__ = "notes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="SET NULL"), index=True)
    title = db.Column(db.String(180), nullable=False)
    content = db.Column(db.Text, nullable=False, default="")
    tags = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="notes")
    subject = db.relationship("Subject", back_populates="notes")


class Quiz(db.Model):
    __tablename__ = "quizzes"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="SET NULL"), index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    user = db.relationship("User", back_populates="quizzes")
    subject = db.relationship("Subject", back_populates="quizzes")
    questions = db.relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan",
                                order_by="QuizQuestion.order_index")
    attempts = db.relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(db.Model):
    __tablename__ = "quiz_questions"

    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = db.Column(db.Integer, nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=False)
    correct_answer = db.Column(db.String(500), nullable=False)
    explanation = db.Column(db.Text, nullable=False, default="")

    quiz = db.relationship("Quiz", back_populates="questions")


class QuizAttempt(db.Model):
    __tablename__ = "quiz_attempts"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)
    total_questions = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    answers = db.Column(db.JSON, nullable=False)
    attempted_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)

    quiz = db.relationship("Quiz", back_populates="attempts")


class Roadmap(db.Model):
    __tablename__ = "roadmaps"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="SET NULL"), index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    user = db.relationship("User", back_populates="roadmaps")
    subject = db.relationship("Subject", back_populates="roadmaps")
    tasks = db.relationship("RoadmapTask", back_populates="roadmap", cascade="all, delete-orphan",
                            order_by="RoadmapTask.sort_order")


class RoadmapTask(db.Model):
    __tablename__ = "roadmap_tasks"

    id = db.Column(db.Integer, primary_key=True)
    roadmap_id = db.Column(db.Integer, db.ForeignKey("roadmaps.id", ondelete="CASCADE"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    completed = db.Column(db.Boolean, nullable=False, default=False)
    due_at = db.Column(db.String(40))
    completed_at = db.Column(db.DateTime(timezone=True))

    roadmap = db.relationship("Roadmap", back_populates="tasks")


class ProgressRecord(db.Model):
    __tablename__ = "progress"
    __table_args__ = (db.UniqueConstraint("user_id", "subject_id", name="uq_progress_user_subject"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    completed_units = db.Column(db.Integer, nullable=False, default=0)
    total_units = db.Column(db.Integer, nullable=False, default=0)
    progress_percent = db.Column(db.Float, nullable=False, default=0)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)

    subject = db.relationship("Subject", back_populates="progress")


class Achievement(db.Model):
    __tablename__ = "achievements"
    __table_args__ = (db.UniqueConstraint("user_id", "achievement_key", name="uq_achievement_user_key"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="SET NULL"))
    achievement_key = db.Column(db.String(120), nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False, default="")
    earned_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)


class AnalyticsSnapshot(db.Model):
    __tablename__ = "analytics"
    __table_args__ = (db.UniqueConstraint("user_id", "snapshot_date", name="uq_analytics_user_day"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    snapshot_date = db.Column(db.Date, nullable=False)
    study_minutes = db.Column(db.Integer, nullable=False, default=0)
    session_count = db.Column(db.Integer, nullable=False, default=0)
    completed_tasks = db.Column(db.Integer, nullable=False, default=0)
    average_quiz_score = db.Column(db.Float)
    roadmap_completion_percent = db.Column(db.Float, nullable=False, default=0)
    notes_count = db.Column(db.Integer, nullable=False, default=0)
    generated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now)


class AITutorHistory(db.Model):
    __tablename__ = "ai_tutor_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="SET NULL"))
    question = db.Column(db.Text, nullable=False)
    response = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(80), nullable=False, default="manual")
    model_name = db.Column(db.String(120), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)


class RevisionPlan(db.Model):
    __tablename__ = "revision_planner"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = db.Column(db.Integer, db.ForeignKey("subjects.id", ondelete="SET NULL"))
    note_id = db.Column(db.Integer, db.ForeignKey("notes.id", ondelete="SET NULL"))
    title = db.Column(db.String(180), nullable=False)
    due_at = db.Column(db.String(40), nullable=False)
    interval_days = db.Column(db.Integer, nullable=False, default=1)
    status = db.Column(db.String(20), nullable=False, default="scheduled")
    completed_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
