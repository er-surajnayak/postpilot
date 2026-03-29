# PostPilot — Social Media Scheduler

A fullstack YouTube post scheduler with a clean UI. Schedule videos, Shorts,
set privacy, upload thumbnails — all from a browser.

---

## Project Structure

```
social-scheduler/
├── backend/
│   ├── main.py           # FastAPI app — all API routes
│   ├── auth.py           # Google OAuth flow
│   ├── youtube.py        # Upload + thumbnail logic
│   ├── scheduler.py      # APScheduler job queue
│   ├── models.py         # Pydantic data models
│   ├── requirements.txt
│   └── .env.example      # Copy this to .env and fill in credentials
└── frontend/
    ├── src/
    │   ├── App.jsx        # Router + sidebar layout
    │   ├── api.js         # Axios API client
    │   ├── pages/
    │   │   ├── Connect.jsx  # Account connection (OAuth)
    │   │   ├── Compose.jsx  # Post composer
    │   │   └── Queue.jsx    # Scheduled posts dashboard
    │   └── index.css
    ├── index.html
    ├── vite.config.js
    ├── tailwind.config.js
    └── package.json
```

---

## Setup (one time)

### Step 1 — Google Cloud credentials

1. Go to https://console.cloud.google.com
2. Create a project (or use existing one)
3. Enable **YouTube Data API v3**
   - APIs & Services → Library → search "YouTube Data API v3" → Enable
4. Create OAuth credentials
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: **Web Application**
   - Name: PostPilot (or anything)
   - Authorized redirect URIs: `http://localhost:8000/auth/callback`
   - Click Create → Copy the **Client ID** and **Client Secret**
5. OAuth consent screen
   - User Type: External
   - Add your Gmail as a Test User

---

### Step 2 — Backend setup

```bash
cd backend

# Copy env file and fill in your credentials
cp .env.example .env
# Open .env and paste your GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Run the backend
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at:     http://localhost:8000/docs

---

### Step 3 — Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Run the frontend
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Usage

1. Open http://localhost:5173
2. Go to **Accounts** tab → click **Connect YouTube Account**
3. Choose your Google account → click Allow
4. You're connected! Go to **New Post** to schedule a video
5. Check **Queue** tab to track upload status

---

## API Endpoints

| Method | Endpoint                        | Description                    |
|--------|---------------------------------|--------------------------------|
| GET    | /auth/login                     | Redirect to Google OAuth       |
| GET    | /auth/callback                  | OAuth callback (Google calls this) |
| GET    | /auth/accounts                  | List connected accounts        |
| DELETE | /auth/accounts/{channel_id}     | Disconnect an account          |
| POST   | /posts/upload                   | Upload/schedule a post         |
| GET    | /posts                          | Get all posts                  |
| GET    | /posts/{job_id}                 | Get single post status         |
| DELETE | /posts/{job_id}                 | Cancel a post                  |
| GET    | /youtube/{channel_id}/videos    | List channel videos            |
| GET    | /health                         | Health check                   |

---

## Environment Variables (.env)

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
SECRET_KEY=any_random_string
```

---

## Adding More Platforms

The backend is structured to add more platforms easily:

1. Create `twitter.py` / `instagram.py` etc. in backend/
2. Add OAuth routes in `auth.py`
3. Add upload function mirroring `youtube.py`
4. Add a platform selector in `Compose.jsx`

The scheduler in `scheduler.py` is platform-agnostic —
just call the right publisher inside `run_upload_job()`.
