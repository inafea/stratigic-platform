# Plan: Accounts, pricing plans and paid subscriptions for "مستشار"

## Context
The app works end to end: idea → questions → 8-section report → chat, in Arabic and English. But anyone who opens it can use it, every report costs real AI calls, and there is no way to earn money. The goal:
- Users **create an account** (email + password, or Google).
- At sign-up they answer a short quiz, and the app **recommends the plan that fits them best**.
- Plans set **limits** on reports, chat, regeneration, model quality and features.
- Paid plans are charged through **Moyasar** (mada, Apple Pay, STC Pay, cards).
- Prices are shown in **SAR and USD**.

Decisions made: Moyasar · SAR + USD · Email + Google sign-in.

---

## 1. Pricing model (proposal)

Basis: one report is about 10 AI calls. Costs per report are roughly 0.01–0.05 USD on Gemini Flash and 0.10–0.30 USD on Claude Haiku/Sonnet. Prices leave a large margin and room for a better model on paid plans.

| Plan | Who it's for | Monthly | Yearly (−20%) | Reports/mo | Chat / report | Model | Features |
|---|---|---|---|---|---|---|---|
| **Free** (مجاني) | Trying it out | 0 | 0 | 2 | 5 messages | Standard (Flash-Lite) | Auto template only, PDF with watermark |
| **Entrepreneur** (رائد أعمال) | Someone testing one or two ideas | 49 SAR / 13 USD | 470 SAR / 125 USD | 10 | 30 | Standard (Flash) | All industry/strategy templates, regenerate, clean PDF |
| **Pro** (احترافي) | Consultants, serious founders | 149 SAR / 39 USD | 1,430 SAR / 375 USD | 40 | Unlimited (fair use) | **Premium** (Claude/Gemini Pro) | Everything + priority, idea comparison (later), Word export (later) |
| **Business** (أعمال) | Agencies, incubators, teams | 499 SAR / 129 USD | 4,790 SAR / 1,240 USD | 150 shared | Unlimited | Premium | Up to 5 seats, branded PDF (company logo), API access (later) |
| **Report pack** (باقة تقارير) | Occasional users, no subscription | 29 SAR / 8 USD for 1 report · 119 SAR / 32 USD for 5 | — | credits, valid 12 months | 30 | Premium | Same features as Pro, for those reports only |

Rules:
- Quotas reset each billing month. Unused reports don't roll over, but pack credits do.
- At the limit: the user sees an upgrade offer and can buy a pack. Nothing gets cut off mid-report: the quota check runs **before** analysis starts.
- Prices, limits and plan names live in **one config file**, not in code, so they can be tuned without a release.

## 2. "Most fit plan" recommender
After registration, a 4-question onboarding quiz (skippable), in Arabic and English:
1. Who are you? (individual with an idea / founder of an existing business / consultant / agency or incubator)
2. How many ideas or analyses do you expect per month? (1 / 2–10 / 10–40 / more than 40)
3. Do you work with a team? (no / 2–5 people)
4. What matters most? (try it free / detailed analysis / client-ready reports)

A rule-based scorer maps the answers to a plan, shows **why** ("You expect around 15 analyses a month for clients → Pro"), and offers the next plan down as an alternative. Users can always pick another plan. The answers are saved, which helps with marketing and tuning prices.

## 3. Architecture

**Accounts and auth (backend):**
- New tables, alongside the existing SQLModel tables in `backend/db.py`:
  - `User`: email, password hash or Google id, name, language, verified, created.
  - `Session`: auth sessions.
  - `EmailToken`: email verification and password reset.
- Passwords are hashed with `argon2` (argon2-cffi).
- Sessions use an **HttpOnly, Secure, SameSite=Lax cookie**, plus CSRF protection on state-changing requests. No tokens are kept in localStorage.
- Google sign-in uses the OAuth 2.0 / OpenID Connect authorization-code flow via `authlib`.
- Email is sent through a small `Mailer` interface: SMTP or a provider such as Resend or SES, with a console mailer for development and tests.
- Ownership: `Report` gets a `user_id`. Every `/api/reports*` route is filtered by the current user. Reports created before this change get attached to an admin account by a migration, using the existing `_add_missing_columns` pattern.

**Plans, quotas, usage:**
- `backend/billing/plans.py` loads `plans.yaml`: price in SAR and USD per period, limits and feature flags.
- New tables:
  - `Subscription`: user, plan, period (monthly/yearly), status, current period start and end, card token, cancel at period end.
  - `UsageEvent`: user, kind (report / chat / regenerate), report_id, at.
  - `CreditPack`: remaining credits, expiry date.
- An `entitlements(user)` service returns the effective plan, the remaining quota and feature flags.
- A FastAPI dependency, `require_quota("report")`, guards `/api/analyze`, `/api/clarify`, the chat route and the regenerate route. Over the limit, it returns **402** with an Arabic/English message plus an `upgrade` hint, reusing `backend/i18n.py`.
- Model per plan: `get_analyzer()` in `backend/main.py` picks the LLM settings from the plan's `model_tier`. Standard and premium tiers are configured in `.env`.

**Payments (Moyasar):**
- `backend/billing/moyasar.py` uses Moyasar's REST API through the existing `httpx` stack, behind a `PaymentProvider` interface so it can be tested with a fake.
- Checkout uses the Moyasar payment form on the client (mada, Apple Pay, STC Pay, cards) with `save_card` and tokenization. The server **verifies the payment by fetching it from Moyasar**; a callback URL alone is never trusted.
- Renewals: Moyasar has no built-in subscription billing, so a daily background job charges the saved card token at period end. It retries on day 1 and day 3, then moves the plan back to Free. Receipts are emailed.
- Webhooks: a `/api/billing/webhook` endpoint with signature/secret check and idempotency, which records each event id once.
- Currency: SAR is the primary charge currency. USD prices are shown to non-Arabic users. **To verify during the Moyasar setup step:** whether the merchant account can charge in USD. If it can't, the checkout charges the SAR equivalent and says so.
- Invoices: VAT-compliant invoices for Saudi customers (15% VAT, ZATCA e-invoicing) are **phase 2**. They need the business's VAT registration and are listed as a later task.

**Frontend:**
- New views:
  - Login and register, with a "Sign in with Google" button.
  - Verify-email notice and forgot/reset password.
  - Onboarding quiz with the recommendation.
  - Pricing page (cards with a monthly/yearly toggle and SAR/USD shown by language).
  - Checkout (Moyasar form).
  - Account page: plan, usage bars, renewal date, cancel or change plan, invoices.
- Header shows the user menu and remaining reports. A 402 response opens an upgrade dialog.
- All text goes through the existing `I18N` dictionary in `frontend/app.js`, and the views work in dark mode.
- The app is still a single page. Simple hash routing (`#/login`, `#/pricing`, `#/account`) is added to `app.js`, with no framework.

**Admin (minimal):** a CLI script, `python -m backend.admin`, to list users, grant a plan and add credits. A web admin panel is not in this round.

## 4. Steps and tasks (one task = one commit on a new branch `feature/accounts-billing`)

**Step A: Accounts**
| # | Task | Done when |
|---|---|---|
| [x] P1 | `User`, `Session` and `EmailToken` tables, plus a migration that attaches existing reports to an admin user | Tables are created and old reports are still readable by the admin |
| [x] P2 | Register, login and logout with argon2, HttpOnly session cookie and CSRF; `current_user` dependency | Tests: register → login → `/api/me` → logout |
| [x] P3 | Email verification and password reset (Mailer interface, console mailer in development) | Tests with the console mailer pass |
| [x] P4 | Google sign-in (OIDC with PKCE, built on httpx instead of authlib) and account linking by verified email | Login works with a test Google client; mocked flow tested |
| [x] P5 | Reports are owned by a user: all report routes filtered by user; 401 when logged out | User A cannot read or delete user B's report (test) |
| [x] P6 | Frontend: login, register, reset and verify views, user menu, hash routing, translations | Full sign-up flow works in the browser in AR and EN, light and dark |

**Step B: Plans and limits**
| # | Task | Done when |
|---|---|---|
| [x] P7 | `plans.toml` (TOML: built into Python, no new package) and loader (prices in SAR/USD, limits, features, model tier) | Schema-validated at startup; test |
| [ ] P8 | `Subscription`, `UsageEvent` and `CreditPack` tables; `entitlements()` service; monthly reset logic | Unit tests for quota math, period boundaries and pack credits |
| [ ] P9 | `require_quota` guard on clarify, analyze, chat and regenerate; 402 with bilingual upgrade message; plan-based model choice in `get_analyzer` | Over-limit Free user gets 402; Pro user gets the premium model (tests) |
| [ ] P10 | Feature flags: templates locked on Free, PDF watermark on Free, chat limit per report | UI hides or locks features; server enforces them too (tests) |

**Step C: Recommender and pricing page**
| # | Task | Done when |
|---|---|---|
| [ ] P11 | Onboarding quiz API, rule-based recommender with a "why" text, answers stored | Table-driven tests cover every answer combination |
| [ ] P12 | Frontend: quiz after sign-up, pricing page (monthly/yearly, SAR/USD), recommended plan highlighted, usage shown in the header | Flow works end to end with Free selected |

**Step D: Payments (Moyasar)**
| # | Task | Done when |
|---|---|---|
| [ ] P13 | `PaymentProvider` interface, Moyasar client and a fake provider; checkout endpoint; server-side payment verification; subscription activation | Test-mode card payment activates Pro (sandbox keys) |
| [ ] P14 | Webhook endpoint (secret check, idempotent) and pack purchases | Replayed webhook doesn't double-credit (test) |
| [ ] P15 | Renewal job (daily): charge saved token, retries, downgrade to Free, receipt and failure emails; cancel at period end; plan change (upgrade now, downgrade at renewal) | Time-travel tests for renew, fail and downgrade |
| [ ] P16 | Account page: plan, usage, next renewal, cancel or change, payment history | Works in the browser in AR/EN, light/dark |

**Step E: Hardening and launch**
| # | Task | Done when |
|---|---|---|
| [ ] P17 | Security pass: login rate limits, account lockout, secure cookie flags behind HTTPS, secrets only in `.env`, audit log of billing events | `/security-review` clean |
| [ ] P18 | Admin CLI (grant plan, add credits, list users) and README/PLAN updates | Documented and working |
| [ ] P19 | Production setup: HTTPS domain, Moyasar live keys, Google OAuth production client, real email provider; Postgres recommended instead of SQLite for multi-user | Staging deployment passes a live purchase with a real card (refunded) |
| Later | ZATCA e-invoicing and VAT invoices; team seats management UI (Business); idea comparison; Word/PPT export; API keys | — |

## 5. What you need to prepare (outside the code)
- **Moyasar merchant account:** needs a Saudi commercial registration. Test keys are enough for P13–P15; live keys are needed for P19.
- **Google Cloud OAuth client:** consent screen, plus redirect URLs for local and production.
- **Email sending:** a domain plus a provider (e.g. Resend, SES or Zoho SMTP).
- **Legal pages:** terms of service, privacy policy (PDPL), refund policy. These are required by Moyasar and Google.
- **Final say on the prices** in section 1. They are a proposal, and the config file makes them easy to change.

## Verification
- `pytest` for each task: auth, ownership, quota math, recommender table, fake payment provider, webhook idempotency, renewal time-travel.
- Manual end-to-end on `uvicorn` with Moyasar **test mode**, in AR and EN and in light and dark:
  1. Register with email, then with Google.
  2. Take the quiz and get a recommendation.
  3. Use up the Free quota and see the 402 upgrade dialog.
  4. Pay for Pro with a Moyasar test card, see the premium model used, then cancel.
- Logged-out user and cross-user access attempts must fail (401/404).
- Do not push without approval (standing rule).
