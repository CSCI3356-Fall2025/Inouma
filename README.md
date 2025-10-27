# Inouma — Authentication tidy-up

What I changed

- Root/landing behavior

  - Root URL (`/`) now redirects to the HTML login page at `/auth/login/` (named `auth-login-page`).
  - The original `landing.html` is left in place but the app no longer serves it at `/` by default.

- Browser session login flow

  - Added a simple form-based login view (`accounts.views.login_view`) and a logout view (`accounts.views.logout_view`).
  - Login form template: `templates/accounts/login.html`.
  - After successful login, users are redirected to `/home` (view name `machine_directory`).

- Protected pages

  - `machine_directory` and `my_reservations` are now decorated with `@login_required` so they require an authenticated session.
  - `staff_dashboard` remains protected with `@staff_member_required` as before.

- Authentication backend

  - Added `accounts.backends.model_backend.EmailBackend` to authenticate users by email/password for the custom `User` model.
  - Left the default `django.contrib.auth.backends.ModelBackend` in place so admin access still works.

- Firebase / DRF changes

  - `accounts.firebase_auth.firebase_authentication.FirebaseAuthentication` now lazy-imports `firebase_admin` inside `authenticate()` to avoid import-time dependency failures.
  - `Inouma/settings.py` now reads Firebase keys using `python-decouple` (`env_config`) and uses logging for warnings (so the development autoreloader doesn't print duplicate messages).
  - REST framework still uses the Firebase authentication class for API endpoints. The browser login uses Django session auth and does not depend on Firebase.

- Minor additions
  - Added `accounts/backends/model_backend.py` with `EmailBackend`.

How to run (development)

1. Create and activate your virtualenv (you already have a `.venv` in the project root):

```bash
cd /Users/charlestang06/Desktop/Inouma
source .venv/bin/activate
```

2. Install dependencies (if not already installed):

```bash
pip install -r requirements.txt
```

3. If you use Firebase/pyrebase features, provide Firebase credentials via a `.env` file next to `manage.py` or export the env vars in your shell:

```text
# .env (example)
SECRET_KEY=your-secret
DEBUG=True
FIREBASE_API_KEY=...
FIREBASE_AUTH_DOMAIN=...
FIREBASE_DATABASE_URL=...
FIREBASE_STORAGE_BUCKET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/oauth2callback
```

4. Run migrations and start the server:

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

5. Visit `http://localhost:8000/` — it will redirect to `/auth/login/`. Use an existing user account or create a user via the API endpoint `/auth/sign-up/` (this endpoint still calls Pyrebase to create Firebase user if configured).

Notes and guidance

- Two authentication flows exist now:

  - Browser/session authentication (form at `/auth/login/`) — uses Django `authenticate()` and session cookies. This is the default for human users navigating the website.
  - API/Firebase authentication — DRF endpoints still use the `FirebaseAuthentication` class. That class is now lazy and will raise a clear error if `firebase-admin` is not available.

- If you prefer to rely solely on Django's authentication (no Firebase), you can:

  - Remove or replace the REST framework `DEFAULT_AUTHENTICATION_CLASSES` in `Inouma/settings.py` with `'rest_framework.authentication.SessionAuthentication'`.
  - Remove pyrebase/firebase admin dependencies from `requirements.txt`.

- I intentionally did not delete the original API views (signup/login) — they remain available for API-driven flows (mobile clients, etc.).

Files changed / added

- Modified

  - `Inouma/settings.py` — firebase env handling, logging, login redirect settings, auth backends
  - `Inouma/urls.py` — root redirect to `/auth/login/`
  - `Inouma/views.py` — added `@login_required` to `machine_directory` and `my_reservations`
  - `accounts/firebase_auth/firebase_authentication.py` — lazy import
  - `accounts/views.py` — added `login_view` and `logout_view` (keeps API views intact)
  - `accounts/urls.py` — added `login/` and `logout/` routes

- Added
  - `templates/accounts/login.html` — simple login form
  - `accounts/backends/model_backend.py` — `EmailBackend` implementation
  - `README.md` (this file)

If you'd like

- I can switch completely to Django's `LoginView`/`LogoutView` from `django.contrib.auth.views` for a more "standard" setup.
- I can add a small unit test that verifies the login redirect works and that `/home` returns 302 for anonymous and 200 for logged-in users.

Tell me which of these you'd like next (tests, switch to built-in auth views, remove Firebase API endpoints, or anything else) and I'll apply it.
