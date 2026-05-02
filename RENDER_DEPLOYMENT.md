# Render Deployment

## Hosted URLs

Replace `<your-service>` with the Render service name.

- User login: `https://<your-service>.onrender.com/`
- User dashboard: `https://<your-service>.onrender.com/user`
- Therapist portal: `https://<your-service>.onrender.com/therapist`
- Admin login: `https://<your-service>.onrender.com/admin`
- Admin console: `https://<your-service>.onrender.com/tm-console-7f3a9c`
- Health check: `https://<your-service>.onrender.com/healthz`

## Free Render Deploy

1. Push this project to GitHub.
2. In Render, create a new Blueprint and connect the repo.
3. Render will read `render.yaml` and use:
   - Plan: `free`
   - Build command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start command: `gunicorn -w 1 --worker-class eventlet -b 0.0.0.0:$PORT app:app`
4. Set the secret environment variables when Render asks:
   - `ADMIN_SIGNUP_CODE`: private code needed to create admin accounts

Paystack keys can be added later from the Render Environment page if you turn on live payments.

## Bot Protection

The app blocks basic signup scripts with server-side signup rate limits, a hidden bot trap field, and a minimum form time check.

For stronger free protection, create Cloudflare Turnstile keys and add these Render environment variables:

- `TURNSTILE_SITE_KEY`
- `TURNSTILE_SECRET_KEY`

When both are set, `/signup` requires a valid Turnstile token verified by the Flask backend.

## Real Email Verification

New user and therapist accounts must verify email ownership before login. Add SMTP environment variables in Render:

- `APP_BASE_URL`: your Render URL, for example `https://therapist-match-lhh8.onrender.com`
- `SMTP_HOST`: for Gmail, `smtp.gmail.com`
- `SMTP_PORT`: usually `587`
- `SMTP_USERNAME`: the email account sending messages
- `SMTP_PASSWORD`: SMTP/app password
- `SMTP_FROM_EMAIL`: the sender email
- `SMTP_FROM_NAME`: for example `TherapistMatch`
- `SMTP_USE_SSL`: `0` for port `587`

For Gmail, use a Google app password instead of your normal Gmail password.

## Free Plan Storage Warning

This free setup uses SQLite and local uploads on Render's temporary filesystem. It is good for a demo, but accounts, admin users, bookings, uploaded therapist documents, and payments can disappear when the service redeploys, restarts, or spins down.

For permanent storage later, move the database to Postgres and uploaded files to object storage, or upgrade the Render service and attach a persistent disk.

## First Admin

After deploy, open `/admin`, enter the admin email and password, choose **Create First Admin**, and enter `ADMIN_SIGNUP_CODE`. After login, you will land on `/tm-console-7f3a9c`.
