import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import inspect

from app import create_app
from app.extensions import db
from app.models import User


class StudyXBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "studyx-test.sqlite3"
        self.apps = []
        self.app = self.make_app()
        self.client = self.app.test_client()

    def tearDown(self):
        for app in self.apps:
            with app.app_context():
                db.session.remove()
                db.engine.dispose()
        self.temp_dir.cleanup()

    def make_app(self):
        app = create_app({
            "TESTING": True,
            "SECRET_KEY": "test-secret",
            "DATABASE": str(self.database_path),
            "SQLALCHEMY_DATABASE_URI": f"sqlite:///{self.database_path.as_posix()}",
        })
        self.apps.append(app)
        return app

    def register(self, client=None, email="student@example.edu", name="Study Student"):
        return (client or self.client).post("/signup", data={
            "display_name": name,
            "email": email,
            "password": "study-password-123",
            "confirm_password": "study-password-123",
        }, follow_redirects=False)

    def test_database_initializes_and_registration_hashes_password(self):
        unauthenticated = self.client.get("/api/studyx/notes")
        self.assertEqual(unauthenticated.status_code, 401)
        login_page = self.client.get("/login")
        self.assertEqual(login_page.status_code, 200)
        self.assertIn(b"StudyX AI", login_page.data)

        response = self.register()
        self.assertEqual(response.status_code, 302)
        dashboard_page = self.client.get("/")
        self.assertEqual(dashboard_page.status_code, 200)
        self.assertIn(b"StudyX AI", dashboard_page.data)
        self.assertEqual(self.client.get("/api/tasks").json, [])
        with self.app.app_context():
            user = User.query.filter_by(email="student@example.edu").one()
            self.assertNotEqual(user.password_hash, "study-password-123")
            self.assertEqual(user.profile.full_name, "Study Student")
            table_names = set(inspect(db.engine).get_table_names())
            self.assertTrue({
                "users", "user_profiles", "subjects", "study_sessions", "notes", "quizzes",
                "quiz_questions", "quiz_attempts", "roadmaps", "roadmap_tasks", "progress",
                "achievements", "analytics", "ai_tutor_history", "revision_planner",
            }.issubset(table_names))
        migration = self.app.test_cli_runner().invoke(args=["db", "upgrade"])
        self.assertEqual(migration.exit_code, 0, migration.output)

    def test_profile_and_notes_crud_are_saved_to_the_account(self):
        self.register()
        subject_response = self.client.post("/api/studyx/subjects", json={
            "name": "Biology", "category": "Semester 3", "color": "mint",
        })
        self.assertEqual(subject_response.status_code, 201)
        subject_id = subject_response.json["id"]

        note_response = self.client.post("/api/studyx/notes", json={
            "subject_id": subject_id, "title": "Cell structure",
            "content": "Mitochondria produce ATP.", "tags": ["cells", "revision"],
        })
        self.assertEqual(note_response.status_code, 201)
        note_id = note_response.json["id"]
        self.assertEqual(self.client.get("/api/studyx/notes").json[0]["content"], "Mitochondria produce ATP.")
        self.assertEqual(self.client.patch(f"/api/studyx/notes/{note_id}", json={
            "content": "Updated biology note.",
        }).status_code, 200)

        profile = self.client.patch("/api/studyx/profile", json={
            "full_name": "Aarav Student", "course_name": "B.Tech",
            "preferences": {"weekly_goal_hours": 10, "reminders_enabled": True},
        })
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json["preferences"]["weekly_goal_hours"], 10)
        self.assertEqual(self.client.delete(f"/api/studyx/notes/{note_id}").status_code, 200)
        self.assertEqual(self.client.get("/api/studyx/notes").json, [])

    def test_quiz_attempt_is_graded_and_averaged_from_saved_scores(self):
        self.register()
        subject = self.client.post("/api/studyx/subjects", json={"name": "Astronomy"}).json
        response = self.client.post("/api/studyx/quizzes", json={
            "title": "Space basics", "subject_id": subject["id"],
            "questions": [
                {"prompt": "Which planet is known as the Red Planet?",
                 "options": ["Mars", "Venus", "Mercury"], "correct_answer": 0,
                 "explanation": "Iron oxide gives Mars its red appearance."},
                {"prompt": "How many moons does Earth have?",
                 "options": ["One", "Two"], "correct_answer": "One"},
            ],
        })
        self.assertEqual(response.status_code, 201)
        quiz_id = response.json["id"]
        question_ids = [question["id"] for question in response.json["questions"]]
        self.assertNotIn("correct_answer", response.json["questions"][0])

        attempt = self.client.post(f"/api/studyx/quizzes/{quiz_id}/attempts", json={
            "answers": {str(question_ids[0]): "Mars", str(question_ids[1]): "Two"},
        })
        self.assertEqual(attempt.status_code, 201)
        self.assertEqual(attempt.json["score"], 1)
        self.assertEqual(attempt.json["percentage"], 50)
        self.assertEqual(len(self.client.get(f"/api/studyx/quizzes/{quiz_id}/attempts").json), 1)
        self.assertEqual(self.client.get("/api/studyx/dashboard").json["quizzes"]["average_score"], 50)

    def test_roadmap_completion_updates_progress_and_achievement(self):
        self.register()
        subject = self.client.post("/api/studyx/subjects", json={"name": "Python"}).json
        roadmap = self.client.post("/api/studyx/roadmaps", json={
            "subject_id": subject["id"], "title": "Python foundations",
            "tasks": ["Variables", "Functions"],
        })
        self.assertEqual(roadmap.status_code, 201)
        roadmap_id = roadmap.json["id"]
        task_ids = [task["id"] for task in roadmap.json["tasks"]]

        partial = self.client.patch(
            f"/api/studyx/roadmaps/{roadmap_id}/tasks/{task_ids[0]}",
            json={"completed": True},
        )
        self.assertEqual(partial.json["completion_percent"], 50)
        self.client.patch(f"/api/studyx/roadmaps/{roadmap_id}/tasks/{task_ids[1]}",
                          json={"completed": True})
        progress = self.client.get("/api/studyx/progress").json
        self.assertEqual(progress["subjects"][0]["progress_percent"], 100)
        self.assertEqual(len(progress["achievements"]), 1)
        summary = self.client.get("/api/studyx/dashboard").json
        self.assertEqual(summary["roadmaps"]["completion_percent"], 100)
        self.assertEqual(summary["roadmaps"]["completed_count"], 1)

    def test_sessions_revision_schedule_tutor_history_and_analytics_are_persistent(self):
        self.register()
        subject = self.client.post("/api/studyx/subjects", json={"name": "Chemistry"}).json
        now = datetime.now(timezone.utc)
        session = self.client.post("/api/sessions", json={
            "subject": "Chemistry", "planned_minutes": 60, "actual_minutes": 48,
            "completed": True, "started_at": now.isoformat(), "source": "focus",
        })
        self.assertEqual(session.status_code, 201)
        self.assertEqual(len(self.client.get("/api/sessions").json), 1)
        summary = self.client.get("/api/studyx/dashboard").json
        self.assertEqual(summary["study"]["total_minutes"], 48)
        self.assertEqual(summary["analytics"]["study_minutes"], 48)

        revision = self.client.post("/api/studyx/revision-planner", json={
            "subject_id": subject["id"], "title": "Review chemical bonds",
            "due_at": (now + timedelta(days=1)).isoformat(), "interval_days": 3,
        })
        self.assertEqual(revision.status_code, 201)
        revision_id = revision.json["id"]
        updated = self.client.patch(f"/api/studyx/revision-planner/{revision_id}", json={
            "status": "completed",
        })
        self.assertEqual(updated.json["status"], "completed")
        self.assertEqual(self.client.get("/api/studyx/revision-planner").json[0]["status"], "completed")

        tutor = self.client.post("/api/studyx/tutor-history", json={
            "subject_id": subject["id"], "question": "Explain covalent bonds.",
            "response": "Atoms share electron pairs in a covalent bond.",
            "provider": "local-demo",
        })
        self.assertEqual(tutor.status_code, 201)
        history_id = tutor.json["id"]
        changed_history = self.client.patch(f"/api/studyx/tutor-history/{history_id}", json={
            "response": "An atom shares electrons to form a covalent bond.",
        })
        self.assertEqual(changed_history.status_code, 200)
        self.assertEqual(self.client.get("/api/studyx/tutor-history").json[0]["question"],
                         "Explain covalent bonds.")
        self.assertEqual(self.client.delete(f"/api/studyx/tutor-history/{history_id}").status_code, 200)
        self.assertEqual(self.client.get("/api/studyx/tutor-history").json, [])
        self.assertEqual(len(self.client.get("/api/studyx/analytics").json), 1)

    def test_user_data_is_isolated_and_persists_after_app_restart(self):
        self.register(email="first@example.edu", name="First Student")
        note = self.client.post("/api/studyx/notes", json={
            "title": "Private note", "content": "Only the first account can read this.",
        }).json
        self.assertEqual(note["title"], "Private note")

        other_client = self.app.test_client()
        self.register(other_client, "second@example.edu", "Second Student")
        self.assertEqual(other_client.get("/api/studyx/notes").json, [])
        self.assertEqual(other_client.patch(f"/api/studyx/notes/{note['id']}", json={
            "content": "Attempted access",
        }).status_code, 404)

        restarted_app = self.make_app()
        restarted_client = restarted_app.test_client()
        response = restarted_client.post("/login", data={
            "email": "first@example.edu", "password": "study-password-123",
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(restarted_client.get("/api/studyx/notes").json[0]["content"],
                         "Only the first account can read this.")

    def test_existing_sqlite_records_survive_schema_upgrade(self):
        schema = Path(__file__).parents[1] / "app" / "schema.sql"
        with closing(sqlite3.connect(self.database_path)) as connection:
            with connection:
                connection.executescript(schema.read_text(encoding="utf-8"))
                connection.execute(
                    """INSERT INTO tasks(title,subject,due_at,duration_minutes,priority,status,kind,notes,created_at)
                       VALUES(?,?,?,?,?,?,?,?,?)""",
                    ("Old saved task", "Statistics", None, 35, "medium", "todo", "study", "", "2026-11-01T10:00:00"),
                )

        self.app = self.make_app()
        self.client = self.app.test_client()
        self.register()
        tasks = self.client.get("/api/tasks").json
        legacy = next(task for task in tasks if task["title"] == "Old saved task")
        self.assertEqual(legacy["duration_minutes"], 35)
        self.assertIsNotNone(legacy["user_id"])


if __name__ == "__main__":
    unittest.main()
