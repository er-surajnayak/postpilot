# LinkedIn Publisher — FastAPI + IBM Carbon UI

A full-stack LinkedIn post manager converted from the Colab notebook.

---

## 📁 Project Structure

```
linkedin-publisher/
├── backend/
│   ├── main.py            ← FastAPI app
│   └── requirements.txt
└── frontend/
    └── index.html         ← IBM Carbon UI (single file, open in browser)
```

---

## ⚙️ Backend Setup

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Run the server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`  
Interactive docs at `http://localhost:8000/docs`

---

## 🖥️ Frontend Setup

Just open `frontend/index.html` in your browser — **no build step needed**.

Set the Backend URL field at the bottom of the page to your FastAPI server address (default: `http://localhost:8000`).

---

## 🔑 Getting a LinkedIn Access Token

1. Go to [developer.linkedin.com](https://developer.linkedin.com)
2. Create an app (or use an existing one)
3. Under **Auth**, request an access token with these scopes:
   - `openid`, `profile`, `email` (for profile info)
   - `w_member_social` (for posting)
4. Use the OAuth 2.0 Token Generator in the portal to get a token

---

## 🚀 API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/` | Health check |
| POST | `/auth/verify` | Verify LinkedIn token, return profile |
| POST | `/post/text` | Publish text-only post |
| POST | `/post/image` | Publish post with image upload |
| POST | `/post/video` | Publish post with video upload |

All `/post/*` endpoints accept `multipart/form-data` with:
- `access_token` (str)
- `person_urn` (str)
- `message` (str)
- `scheduled_at` (optional, format: `YYYY-MM-DDTHH:MM`)
- `tz_name` (optional, default: `Asia/Kolkata`)
- `image` / `video` (file, for respective endpoints)

---

## ⚠️ Notes

- LinkedIn's API has **no native scheduling** — the backend uses `time.sleep()` which blocks the worker. For production scheduling, use **Celery + Redis** or **APScheduler**.
- Access tokens expire (typically 60 days) — refresh via OAuth when needed.
- Image limit: **5 MB** | Video limit: **200 MB**
