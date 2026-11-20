# StudyX AI

A student study planner built with Flask, SQLite, SQLAlchemy, HTML, CSS and JavaScript. Existing planner and research features remain in place; the account-linked StudyX backend adds profiles, subjects, notes, quizzes, roadmaps, progress, analytics, revision schedules and tutor history.

## Open and run in PyCharm

1. Open this folder as a project in PyCharm.
2. Create a Python virtual environment from **Settings → Project → Python Interpreter**.
3. Open the PyCharm terminal and install the main dependency:

   ```bash
   pip install -r requirements.txt
   ```

4. Open `run.py` and click **Run**. The development server opens at `http://127.0.0.1:5000`.
5. Open `http://127.0.0.1:5000`, choose **Create an account**, and sign up. SQLite tables initialize automatically at `instance/luma_study.sqlite3`. The app starts empty: it does not save example tasks, subjects, quiz scores or research results.

Sign in with the same email and password on later visits. Passwords are stored as hashes. Planner and StudyX records are isolated by account and remain in SQLite after sign-out or an app restart. Use **Sign out** at the bottom of the sidebar to switch accounts.

For the paired t-test/Wilcoxon calculations in Research Lab, install the optional analysis tools:

```bash
pip install -r requirements-analysis.txt
```

Without SciPy, the Research Lab still saves and exports responses and shows descriptive paired times; it does not invent a p-value.

## Project map

```text
run.py                      Development entry point
app/__init__.py             Flask application factory and blueprint setup
app/database.py             SQLite initialization and backward-compatible upgrades
app/extensions.py           SQLAlchemy and Flask-Migrate extensions
app/models.py               Account-linked SQLAlchemy models and relationships
app/schema.sql              Existing planner and research tables
app/routes/web.py           Page routes
app/routes/api.py           CRUD, measurement, research and CSV API routes
app/routes/studyx_api.py    Profile, notes, quiz, roadmap, progress and tutor APIs
alembic.ini                 Migration settings
migrations/                 Alembic migration environment and revisions
app/templates/base.html     Shared glass-style shell, navigation and task dialog
app/templates/auth.html     Login and account-creation screens
app/templates/pages/        Individual website pages
app/static/css/             Design tokens, layout, components, glass effects and page styles
app/static/js/core/         API helper, icons, UI helpers, visual effects and renderers
app/static/js/pages/        Page-specific interactions
instance/                   Automatically created SQLite data folder
tests/                      Database and API integration tests
```

## Included features

- Create, edit, complete and delete study tasks.
- Weekly calendar view, course progress, exam countdowns and subject filters.
- Focus timer with recorded sessions and recent-session history.
- Dashboard and charts based on real saved planner activity.
- StudyX profile and preference data, with database-backed settings.
- Subject and category CRUD, private notes and tags.
- Quizzes with server-side answer checking and saved attempt history.
- Personal roadmaps with automatic completion percentages and achievements.
- Revision planner and saved AI tutor question/response history.
- Daily analytics snapshots calculated from actual study sessions, quiz attempts and roadmap tasks.
- Basic interaction-event logging for task creation/completion, exams and focus sessions.
- Mixed-format baseline survey, post-task SUS scoring, paired usability-test entry and CSV exports.
- Paired comparison chooses a t-test only when the sample is large enough for a normality check and the paired differences pass it; otherwise it uses the Wilcoxon signed-rank test when SciPy is installed.

## StudyX API

All endpoints below require a signed-in account. JSON values are validated and each query is scoped to the current user.

| Data | Routes |
| --- | --- |
| Profile | `GET`, `PATCH /api/studyx/profile` |
| Subjects | `GET`, `POST /api/studyx/subjects`; `PATCH`, `DELETE /api/studyx/subjects/<id>` |
| Notes | `GET`, `POST /api/studyx/notes`; `PATCH`, `DELETE /api/studyx/notes/<id>` |
| Quizzes and attempts | `GET`, `POST /api/studyx/quizzes`; `GET`, `PATCH`, `DELETE /api/studyx/quizzes/<id>`; `POST`, `GET /api/studyx/quizzes/<id>/attempts` |
| Roadmaps | `GET`, `POST /api/studyx/roadmaps`; `PATCH`, `DELETE /api/studyx/roadmaps/<id>`; task CRUD under `/api/studyx/roadmaps/<id>/tasks` |
| Progress and analytics | `GET /api/studyx/progress`, `GET /api/studyx/analytics`, `GET /api/studyx/dashboard` |
| Tutor history | `GET`, `POST /api/studyx/tutor-history`; `PATCH`, `DELETE /api/studyx/tutor-history/<id>` |
| Revision planner | `GET`, `POST /api/studyx/revision-planner`; `PATCH`, `DELETE /api/studyx/revision-planner/<id>` |

Quiz correct answers stay on the server and attempts are scored there. Tutor history stores the question and response supplied by the app; no AI provider key is stored in the database.

## Database migrations

Tables are created automatically at app startup without dropping existing records. To apply migration revisions manually or create a new one:

```bash
flask --app run.py db upgrade
flask --app run.py db migrate -m "describe schema change"
```

The new StudyX tables use SQLAlchemy relationships and portable column types. SQLite is the configured local database. Plan and migrate existing planner endpoints before switching a deployed database to PostgreSQL.

## Research integrity notes

Use actual participants and participant codes such as `P01`; do not enter names or contact details. A paired test should use the same participant and the same task with both methods. Record how the task was explained and note any order effects. Report the number of participants, test used, effect size, confidence interval, limitations and usability issues in the final college report.

## Before sharing or deploying

Run the requested integration checks with:

```bash
python -m unittest discover -s tests -v
```

Before exposing this classroom prototype to other people, set a private `LUMA_SECRET_KEY` environment variable, add CSRF protection and production hosting safeguards, and avoid collecting personal identifiers in research forms.
