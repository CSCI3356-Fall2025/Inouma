# Inouma

A Django web app for **The Hatchery**, Boston College's student makerspace. Users browse machines, complete required trainings, and reserve equipment; staff manage machines, trainings, reservations, and semester-long team schedules. Built as a team project for CSCI3356 (Software Engineering), Fall 2025.

**Live site:** https://inouma.onrender.com

## Directory Structure

```
├── Inouma/          # Settings, root URLs, dashboards
├── accounts/        # User model, profiles, Google OAuth + email/password login
├── machines/        # Machines, categories, trainings
├── locations/       # Locations, floorplans, capacity
├── reservations/    # Reservations, waitlists, training sessions, maintenance
├── scheduling/      # Semesters, shift requirements, weekly auto-scheduler
├── social/          # Project feed, friends, badges, leaderboard
├── team/            # Team directory and dashboard
├── templates/       # HTML templates, organized by app
├── static/          # CSS, JS, images
├── testing/         # Demo/test data generation scripts
├── manage.py
├── requirements.txt
└── db.sqlite3       # Local development database
```

## Where to Find Code

Each app owns one slice of the system — models in `models.py`, routes in `urls.py`, logic in `views.py`, and matching templates under `templates/<app>/`. The two files worth reading first are `reservations/services.py` (all booking validation) and `scheduling/weekly_scheduler.py` (builds a model week of shifts and replicates it across the semester).

## User Roles

Set by `User.ROLE_CHOICES` in `accounts/models.py`:

- **User** / **Collaborator** — browse machines, book trainings, track certification progress, reserve machines they're certified on, report broken machines, post projects to the social feed
- **Team Member** — the above, plus shift schedules and availability requests. Flags `is_trainer` (runs training sessions) and `is_team_lead` (leads a machine category) layer on top
- **Staff** — manage machines, trainings, and locations; track maintenance and blackouts; configure semesters, run the auto-scheduler, and publish schedules

Django's built-in `is_staff` gates the admin site separately.

## How to Run the Code

```bash
python3 -m venv env_site
source env_site/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Requires a `.env` next to `manage.py` with `SECRET_KEY` and `DEBUG`. Firebase (`FIREBASE_API_KEY`, `FIREBASE_AUTH_DOMAIN`, `FIREBASE_DATABASE_URL`, `FIREBASE_STORAGE_BUCKET`) and Google OAuth (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`) keys are optional locally — without them, those features are skipped and you sign in with email/password.

A fresh clone starts with an empty database, so run `bash testing/setup_demo.sh` to populate it — 52 users, machines, trainings, certifications, and sessions. Log in at `/auth/login/email/` as `test1@gmail.com` (no certifications) or `test2@gmail.com` (Level 1 certifications), password `testpass123`. Reset with `testing/cleanup_all_test_data.py`.

## Non-Standard Libraries & APIs

- **Django REST Framework** — API endpoints for reservations, trainings, and scheduling
- **Google OAuth** — sign-in with BC Google accounts
- **Pyrebase4 / firebase-admin** — Firebase authentication for API clients
- **python-decouple** — reads secrets from `.env`
- **WhiteNoise + Gunicorn** — deployed on Render with PostgreSQL; SQLite locally

## Project Team

Developed by a team of five students in CSCI3356 (Fall 2025): 
- Hansung (Noah) Kang ([@nk2417](https://github.com/nk2417)), 
- Omar Tall ([@Mr-Tall](https://github.com/Mr-Tall)), 
- Lucas Schmidt ([@schmidln](https://github.com/schmidln)), 
- Brianna Tang ([@briannnnat](https://github.com/briannnnat)), 
- Samira Isack ([@samiraisac](https://github.com/samiraisac))
