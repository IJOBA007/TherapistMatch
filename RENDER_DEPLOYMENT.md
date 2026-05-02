# Render Deployment

## Hosted URLs

Replace `<your-service>` with the Render service name.

- User login: `https://<your-service>.onrender.com/`
- User dashboard: `https://<your-service>.onrender.com/user`
- Therapist portal: `https://<your-service>.onrender.com/therapist`
- Admin login: `https://<your-service>.onrender.com/admin`
- Admin console: `https://<your-service>.onrender.com/admin/console`
- Health check: `https://<your-service>.onrender.com/healthz`

## Deploy With `render.yaml`

1. Push this project to GitHub.
2. In Render, create a new Blueprint and connect the repo.
3. Render will read `render.yaml` and use:
   - Build command: `pip install --upgrade pip && pip install -r requirements.txt`
   - Start command: `gunicorn -w 1 --worker-class eventlet -b 0.0.0.0:$PORT app:app`
   - Persistent disk mounted at `/var/data`
4. Set the secret environment variables when Render asks:
   - `ADMIN_SIGNUP_CODE`: private code needed to create admin accounts
   - `PAYSTACK_SECRET_KEY`: your Paystack secret key, if payments are live
   - `PAYSTACK_PUBLIC_KEY`: your Paystack public key, if payments are live

## Important Storage Note

This app uses SQLite and local uploads. On Render, local files are temporary unless they are written to a persistent disk. The included `render.yaml` sets `DATA_DIR=/var/data` and attaches a disk there so `database.db` and uploaded therapist documents survive deploys and restarts.

## First Admin

After deploy, open `/admin`, enter the admin email and password, choose **Create First Admin**, and enter `ADMIN_SIGNUP_CODE`.

