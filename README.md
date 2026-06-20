# విద్యా విజయం (Vidya Vijayam) 🌟

**Vidya Vijayam** is an interactive, gamified Telugu educational application designed for children. Through a delightful "Fishtopia" fishing adventure game, kids learn Telugu vowels (అచ్చులు), consonants (హల్లులు), spelling, vocabulary, and sentence structure. Correct answers earn them bait to catch exotic fish in the virtual pond!

---

## Features 🚀

- **Interactive Telugu Keyboard**: Custom virtual keyboard layout supporting Telugu characters directly.
- **5 Progressive Learning Modules**:
  1. **అచ్చులు & హల్లులు** (Vowels & Consonants recognition)
  2. **పదాల అమరిక** (Spelling Words block arrangement)
  3. **పదాల అర్ధాలు** (Vocabulary translation matching)
  4. **వాక్య నిర్మాణం** (Interactive sentence puzzle building)
  5. **పఠన అవగాహన** (Story comprehension & quizzes)
- **Fishing Minigame**: Catch common, rare, epic, and legendary fish using earned bait! Upgradable fishing rod, bait bucket, and backpack.
- **Custom Curriculum Upload**: Parents and teachers can upload any text-based Telugu syllabus PDF to dynamically populate vocabulary and sentence exercises.

---

## Local Setup & Installation 💻

Follow these steps to run the application locally on your machine.

### Prerequisites
- **Python 3.9 or higher** installed on your system.
- Git (optional, for cloning).

### 1. Clone or Download the Repository
Clone the repository or download the ZIP file:
```bash
git clone https://github.com/hemanthsrisai3/Vidya-Vijayam.git
cd Vidya-Vijayam
```

### 2. Set Up Virtual Environment
Initialize a clean virtual environment to manage dependencies:

* **Windows (PowerShell):**
  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```

* **macOS / Linux:**
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

### 3. Install Dependencies
Install all required libraries using pip:
```bash
pip install -r requirements.txt
```

### 4. Run the Application
Start the Flask development server:
```bash
python app.py
```

Once started, open your web browser and visit:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## Deploying to the Cloud ☁️

Here are two popular options for deploying this Flask application to the cloud.

### Option A: Deploying to Google Cloud Run (Recommended & Scalable)
Cloud Run is a fully managed, serverless platform that automatically scales your containerized application.

#### Step 1: Create a `Dockerfile`
In the root directory of your project, create a file named `Dockerfile` with the following content:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

ENV PORT=8080
EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
```

#### Step 2: Deploy using Google Cloud SDK
1. Make sure you have the [Google Cloud SDK](https://cloud.google.com/sdk) installed and authenticated:
   ```bash
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   ```
2. Build and deploy in one single command:
   ```bash
   gcloud run deploy vidya-vijayam --source . --port 8080 --allow-unauthenticated
   ```
3. Once completed, gcloud will provide you with a public URL!

---

### Option B: Deploying to Render (Quickest & Easiest)
Render is a cloud platform that integrates directly with GitHub for automatic deployments on Git push.

1. **Sign Up**: Create an account on [Render](https://render.com).
2. **New Web Service**: Click **New +** and select **Web Service**.
3. **Connect Repository**: Connect your GitHub account and select your `Vidya-Vijayam` repository.
4. **Configure Settings**:
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app` (Render automatically installs gunicorn if you add it to requirements.txt, or you can use `python app.py` for light development use).
5. **Add Environment Variables** (Optional):
   - Set `FLASK_SECRET_KEY` to a random secure string.
6. **Deploy**: Click **Create Web Service**. Your app will be live in a few minutes!