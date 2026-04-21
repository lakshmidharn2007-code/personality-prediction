# AI Resume Personality Analyzer

Production-style MVP built with Streamlit, Python NLP tooling, and Firebase. The app accepts PDF and DOCX resumes, extracts structured content, predicts resume category using a trained scikit-learn model, infers a transparent rule-based personality tendency, stores results in Firebase, and supports recruiter-style review dashboards.

## Features

- Streamlit UI with sidebar navigation.
- Email/password authentication using Firebase Auth REST API.
- Multi-file upload for PDF and DOCX resumes.
- Resume parsing for name, email, phone, skills, education, experience, and summary.
- Resume category prediction using a persisted `resume_classifier.joblib` model.
- Confidence score display for model output.
- Rule-based `personality_tendency` label with explicit non-diagnostic disclaimer.
- Firebase Storage upload for original resume files.
- Firestore persistence for users, uploads, and analysis results.
- History page with search, filters, and CSV export.
- Admin dashboard for all uploaded analyses.
- Free-plan fallback mode that skips cloud file upload and still saves analysis metadata to Firestore.

## Project Structure

```text
personality prediction/
├── app.py
├── README.md
├── requirements.txt
├── .env.example
├── .streamlit/
│   └── secrets.toml.example
├── models/
│   └── .gitkeep
└── src/
    ├── __init__.py
    ├── auth_service.py
    ├── firebase_config.py
    ├── firestore_service.py
    ├── parser.py
    ├── predictor.py
    ├── rules.py
    ├── storage_service.py
    ├── ui_components.py
    └── utils.py
```

## How It Works

1. User signs in with Firebase Auth.
2. User uploads one or more PDF or DOCX resumes.
3. The parser extracts text and pulls structured candidate details.
4. The predictor loads the trained scikit-learn model and predicts the resume category.
5. A rule-based layer infers a `personality_tendency` label from skills and resume content.
6. The original file is uploaded to Firebase Storage.
7. The structured analysis record is saved to Firestore.
8. The app shows latest results, history, recruiter filters, and CSV downloads.

## Setup

### 1. Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Add your trained model

Place your model in:

```text
models/resume_classifier.joblib
```

Or set:

```text
MODEL_PATH=C:/Users/laksh/Downloads/resume_classifier.joblib
```

If your existing file is at [resume_classifier.joblib](C:\Users\laksh\Downloads\resume_classifier.joblib), either copy it into `models/` or point `MODEL_PATH` to that location.

### 3. Configure Firebase

Create `.streamlit/secrets.toml` from `.streamlit/secrets.toml.example` or export environment variables from `.env.example`.

Required values:

- `FIREBASE_PROJECT_ID`
- `FIREBASE_STORAGE_BUCKET`
- `FIREBASE_WEB_API_KEY`
- `FIREBASE_SERVICE_ACCOUNT_JSON` or `FIREBASE_SERVICE_ACCOUNT_FILE`
- `MODEL_PATH`
- `ENABLE_STORAGE_UPLOADS` set to `false` for Spark/free-plan mode, `true` after you enable Firebase Storage

### 4. Create Firebase service account

1. Open Firebase Console.
2. Go to `Project settings` -> `Service accounts`.
3. Generate a new private key.
4. Store the JSON outside source control.
5. Reference it through `FIREBASE_SERVICE_ACCOUNT_FILE` or inline it in Streamlit secrets.

### 5. Enable Firebase products

Enable:

- Authentication -> Email/Password
- Firestore Database
- Firebase Storage

### 6. Run the app

```powershell
streamlit run app.py
```

## Firebase Configuration

The project already uses these Firebase client values:

```javascript
const firebaseConfig = {
  apiKey: "AIzaSyAJbI-aEL2ro06MVLiBWbR3WSOHEFXZ-Qs",
  authDomain: "personality-prediction-1bc5c.firebaseapp.com",
  projectId: "personality-prediction-1bc5c",
  storageBucket: "personality-prediction-1bc5c.firebasestorage.app",
  messagingSenderId: "639771961586",
  appId: "1:639771961586:web:b1cbf012dfb9215857486b"
};
```

Only the public web config belongs in the client-side auth flow. The admin private key must stay in secrets or environment variables.

## Firestore Schema Design

### `users/{user_id}`

```json
{
  "user_id": "abc123",
  "email": "student@example.com",
  "full_name": "Student Demo",
  "is_admin": false,
  "created_at": "2026-04-19T12:00:00+00:00"
}
```

### `resume_uploads/{upload_id}`

```json
{
  "upload_id": "upload_123",
  "user_id": "abc123",
  "file_name": "resume1.pdf",
  "storage_url": "https://storage.googleapis.com/...",
  "uploaded_at": "2026-04-19T12:00:00+00:00",
  "processing_status": "completed",
  "status": "completed"
}
```

### `analysis_results/{upload_id}`

```json
{
  "user_id": "abc123",
  "file_name": "resume1.pdf",
  "storage_url": "https://storage.googleapis.com/...",
  "predicted_category": "IT",
  "confidence": 0.93,
  "personality_tendency": "Analytical",
  "email": "candidate@email.com",
  "phone": "9876543210",
  "skills": ["python", "sql", "machine learning"],
  "education": "B.Tech Computer Science",
  "experience": "2 years in backend development",
  "summary": "Software engineer focused on APIs and ML tooling",
  "created_at": "2026-04-19T12:00:00+00:00",
  "status": "completed"
}
```

## Firebase Storage Path Scheme

```text
resumes/{user_id}/{upload_id}/{original_file_name}
```

Example:

```text
resumes/abc123/7bc5c7d2-1d18-4eb9-a264-0bdf4de2eab7/resume1.pdf
```

## Free Plan Mode

If you want to stay on Firebase Spark/free tier, keep:

```text
ENABLE_STORAGE_UPLOADS=false
```

In this mode:

- original resume files are not uploaded to Firebase Storage
- `storage_url` is saved as an empty string
- `storage_status` shows `skipped`
- parsed results, predictions, and history still save to Firestore

This is the recommended setup for a student demo if you do not want to enable billing.

## Notes on Personality Tendency

This MVP does not predict personality directly from a machine learning model. The UI and backend both frame `personality_tendency` as a rule-based inference from skills, summary, and experience text. For academic or demo use, keep that disclaimer visible.

## Extending With Your Existing Logic

The main extension points are:

- [src/parser.py](D:\COLLEGE\projects\personality prediction\src\parser.py): replace regex and section extraction with your current parsing pipeline.
- [src/predictor.py](D:\COLLEGE\projects\personality prediction\src\predictor.py): keep your current TF-IDF + LogisticRegression joblib model here.
- [src/rules.py](D:\COLLEGE\projects\personality prediction\src\rules.py): refine the tendency rules and labels.

If your current parser already writes CSV, keep that logic in a helper and feed the same records into Firestore through [src/firestore_service.py](D:\COLLEGE\projects\personality prediction\src\firestore_service.py).

## Suggested Firestore Security Rules

Example starting point:

```text
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }

    match /resume_uploads/{uploadId} {
      allow read, write: if request.auth != null;
    }

    match /analysis_results/{uploadId} {
      allow read, write: if request.auth != null;
    }
  }
}
```

Tighten these for production by checking ownership and admin claims.

## Suggested Storage Rules

```text
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    match /resumes/{userId}/{uploadId}/{fileName} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
```

## Deployment Notes

- Streamlit Community Cloud or Render can host the UI.
- Keep Firebase secrets in the deployment platform's secret manager.
- Ensure the service account key is never committed.
- If you need private file access, replace `blob.make_public()` with signed URLs or authenticated download flows.
