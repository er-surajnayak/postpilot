# PostPilot — Social Media Scheduler

A fullstack social media scheduler with a clean UI. Schedule YouTube videos,
LinkedIn posts, Facebook Page posts, and Instagram Business content from one place.

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

### Step 1 — Get API Credentials

**1. Google Cloud (YouTube)**
- Go to https://console.cloud.google.com and create a project
- Enable **YouTube Data API v3**
- Go to APIs & Services → Credentials → Create OAuth client ID (Web Application)
- Add authorized redirect URI: `http://localhost:8000/auth/callback` (or your production URL `https://your-backend-domain/auth/callback`)
- Copy **Client ID** and **Client Secret**

**2. LinkedIn Developer Portal**
- Go to https://developer.linkedin.com/
- Create an app and enable **Sign In with LinkedIn** and **Share on LinkedIn**
- Add authorized redirect URI: `http://localhost:8000/auth/linkedin/callback` (or your production URL `https://your-backend-domain/auth/linkedin/callback`)
- Copy **Client ID** and **Client Secret**

**3. Meta (Facebook + Instagram)**
- Create a Business app at https://developers.facebook.com/apps
- Add products: `Facebook Login`, `Pages API`, `Instagram Graph API`
- Add authorized redirect URI: `http://localhost:8000/auth/facebook/callback` (and your production URL)
- Copy **App ID** and **App Secret** into `META_APP_ID` and `META_APP_SECRET`.
- When connecting via the frontend, all authorized Facebook Pages and linked Instagram Business accounts will be imported.

---

### Step 2 — Backend setup

```bash
cd backend

# Copy env file and fill in your credentials
cp .env.example .env

# Create virtual environment
python -m venv venv
source venv/bin/activate      # Mac/Linux
# venv\Scripts\activate       # Windows

# Install dependencies
pip install -r requirements.txt

# Run the backend locally
uvicorn main:app --reload --port 8000
```

Backend runs at: http://localhost:8000
API docs at:     http://localhost:8000/docs

*Note on Production Deployments:* Set `FRONTEND_URL` and `BACKEND_URL` in `.env` or in your hosting provider (e.g. Render) to point to your live deployment endpoints. 
**Crucial Instagram Note:** Instagram publishing requires `BACKEND_URL` to be publicly reachable because Meta fetches media from your backend at publish time. However, Facebook Page publishing uses binary uploads directly and functions properly on `localhost`.

---

### Step 3 — Frontend setup

```bash
cd frontend

# Install dependencies
npm install

# Run the frontend locally
npm run dev
```

Frontend runs at: http://localhost:5173

---

## Usage

1. Open frontend app (e.g. http://localhost:5173)
2. Go to **Accounts** tab and use the connect buttons to link your platforms via OAuth.
3. You're connected! Go to **New Post** to schedule or publish immediately!
4. Check **Queue** tab to track upload status.

---

## Environment Variables (.env)

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_GRAPH_VERSION=v23.0
INSTAGRAM_APP_ID=your_instagram_app_id  # Optional, for Instagram Login flow
INSTAGRAM_APP_SECRET=your_instagram_secret
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
