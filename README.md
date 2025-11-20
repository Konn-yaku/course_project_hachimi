# Home Cloud: LAN-based Media Center & File Manager

[Report Video Link](https://youtu.be/XStHJMKqO7Q)

**Home Cloud** is a lightweight, self-hosted storage solution designed for home networks. It combines a traditional file manager with an intelligent media center, powered by **FastAPI** and **TMDB (The Movie Database)** integration.

Unlike complex NAS systems, Home Cloud focuses on simplicity: **No database required**, **Filesystem-based**, and **Open access for LAN usage**.

## **🌟 Key Features**

### 1. **Intelligent Media Upload & Organization**
The core highlight of the system. It transforms a messy file upload process into an organized library.
* **Smart Recognition:** Automatically detects video files during upload.
* **TMDB Integration:** Queries The Movie Database API to identify Movies and TV Shows.
* **Auto-Organization:**
    * Renames/Moves files into dedicated folders based on the official title.
    * **Auto-Poster:** Downloads the official cover art/poster automatically.
* **Fallback:** Non-video files are uploaded normally as standard attachments.

### 2. **Visual Media Library**
Dedicated views for your entertainment collection, separated from raw files.
* **Anime & Movies Views:** Automatically scans your media directories (`/Anime`, `/Movies`) and displays content in a rich gallery grid with posters and titles.
* **Smart Indexing:** Intelligently ignores non-media files (like subtitles or nfo files) when generating the gallery view to keep the interface clean.

### 3. **Full-Featured File Manager**
A robust explorer for managing your server's filesystem.
* **Browse:** Navigate through folders and files seamlessly.
* **Management:** Create new folders (`Mkdir`) and delete unwanted content (`Delete` supports recursive folder deletion).
* **Upload:** Drag-and-drop upload support.

### 4. **LAN-First Architecture**
* **No Authentication:** Intentionally designed without login barriers for frictionless access within a trusted home network (Family/Roommates).
* **Direct Playback:** Stream videos and view images directly in the browser (supports native web formats like MP4, WebM, JPG, PNG, WebP).

---

## **🛠️ Tech Stack**

* **Backend:** Python (FastAPI, Uvicorn)
* **Frontend:** Vanilla HTML/CSS/JS (Single Page Application design)
* **External API:** TMDB (The Movie Database) for metadata processing

---

## **🚀 Installation & Setup**

### 1. Prerequisites
* Python 3.8+
* A TMDB API Key (Get it from [themoviedb.org](https://www.themoviedb.org/))

### 2. Clone & Install
```bash
# Clone the repository
git clone [https://github.com/your-repo/home-cloud.git](https://github.com/your-repo/home-cloud.git)

# Enter backend directory
cd home-cloud/backend

# Create virtual environment
python -m venv .venv

# Activate Virtual Environment:
# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn[standard] requests guessit python-multipart pydantic-settings
```

### 3. Configuration
Create a .env file in the backend directory with the following content:
```bash
# Storage location for your files (ensure this folder exists or the app will create it)
MEDIA_ROOT_PATH="./my_media_files"

# Allow frontend access (CORS Origin)
# If using Live Server, this is usually [http://127.0.0.1:5500](http://127.0.0.1:5500)
FRONTEND_ORIGIN="[http://127.0.0.1:5500](http://127.0.0.1:5500)"

# Required for Smart Uploads
TMDB_API_KEY="YOUR_TMDB_API_KEY_HERE"
```

### 4. Run
Start the backend server:
```bash
uvicorn app.main:app --reload
```
The backend will run at http://127.0.0.1:8000

Start the frontend (using Live Server or any static host) and connect.

## 🔮 Future Roadmap
* Video Transcoding: Implement HLS/DASH for better playback compatibility on mobile devices.

* External Access: Integration with FRP or Tailscale for accessing files outside the home network.

* User System: Re-enable the authentication module (Argon2/JWT) for multi-user support.