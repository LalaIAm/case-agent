# Manual Testing Checklist – Authentication

Use this checklist to verify the JWT-based authentication system.

## Backend

- [ ] **POST /api/auth/register** – Accepts email and password; returns user (and optionally token). Create a new user with valid email and password (min 8 chars).
- [ ] **POST /api/auth/login** – Accepts credentials (form: `username`=email, `password`); returns `access_token` and `token_type`.
- [ ] **GET /api/auth/me** – With valid `Authorization: Bearer <token>` returns current user profile.
- [ ] **GET /api/auth/me** – With no token or invalid token returns 401 Unauthorized.
- [ ] **POST /api/auth/logout** – With valid token returns success (client should discard token).

## Frontend

- [ ] **Registration** – Submit registration form with email and password; account is created and user is redirected to dashboard.
- [ ] **Login** – Submit login form with valid credentials; user is authenticated and redirected to dashboard.
- [ ] **Logout** – Click logout; token is cleared and user is redirected to login.
- [ ] **Protected routes** – Visiting `/` when not authenticated redirects to `/login`.
- [ ] **Axios interceptor** – All API requests include `Authorization: Bearer <token>` when user is logged in.
- [ ] **401 handling** – A 401 response from the API clears token and redirects to login (when not already on login/register).

## Notes

- Login uses form-urlencoded body: `username` (email) and `password`.
- Register uses JSON body: `{ "email": "...", "password": "..." }`.
- Use `Authorization: Bearer <token>` for protected endpoints.
