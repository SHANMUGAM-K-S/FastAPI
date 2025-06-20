from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from uuid import uuid4
import uvicorn
import shutil
import os
import json
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import UploadFile
from email.message import EmailMessage
import smtplib

# Load environment variables
load_dotenv()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Set to specific origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directories
BASE_DIR = Path(__file__).resolve().parent
JOBS_FILE = BASE_DIR / "src/JsonFiles/Jobs.json"
UPLOAD_DIR = BASE_DIR / "src/Uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Serve uploaded images
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


# Data model
class Job(BaseModel):
    id: str
    name: str
    experience: str
    location: str
    description: str
    image: Optional[str] = None


@app.get('/')
def office_website():
    return {"Inspirit Engineering Solutions"}
# Read jobs from file


def read_jobs() -> List[Job]:
    if not JOBS_FILE.exists():
        JOBS_FILE.write_text("[]")
    with open(JOBS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# Write jobs to file
def write_jobs(jobs: List[dict]):
    with open(JOBS_FILE, "w", encoding="utf-8") as f:
        json.dump(jobs, f, indent=2)


# GET all jobs
@app.get("/jobs", response_model=List[Job])
def get_jobs():
    return read_jobs()


# POST a new job
@app.post("/jobs")
def add_job(
    id: str = Form(...),
    name: str = Form(...),
    experience: str = Form(...),
    location: str = Form(...),
    description: str = Form(...),
    image: Optional[UploadFile] = File(None)
):
    jobs = read_jobs()
    image_url = None

    if image:
        filename = f"{uuid4()}_{image.filename}"
        file_path = UPLOAD_DIR / filename
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
        image_url = f"/uploads/{filename}"

    new_job = {
        "id": id,
        "name": name,
        "experience": experience,
        "location": location,
        "description": description,
        "image": image_url
    }

    jobs.append(new_job)
    write_jobs(jobs)
    return {"message": "✅ Job added successfully!", "job": new_job}


# PUT (update) a job
@app.put("/jobs/{job_id}")
def update_job(
    job_id: str,
    name: Optional[str] = Form(None),
    experience: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None)
):
    jobs = read_jobs()
    for job in jobs:
        if job["id"] == job_id:
            if name:
                job["name"] = name
            if experience:
                job["experience"] = experience
            if location:
                job["location"] = location
            if description:
                job["description"] = description
            if image:
                filename = f"{uuid4()}_{image.filename}"
                file_path = UPLOAD_DIR / filename
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(image.file, buffer)
                job["image"] = f"/uploads/{filename}"
            write_jobs(jobs)
            return {"message": "✅ Job updated successfully!", "job": job}
    raise HTTPException(status_code=404, detail="⚠️ Job not found!")


# DELETE a job
@app.delete("/jobs/{job_id}")
def delete_job(job_id: str):
    jobs = read_jobs()
    updated_jobs = [job for job in jobs if job["id"] != job_id]
    if len(jobs) == len(updated_jobs):
        raise HTTPException(status_code=404, detail="⚠️ Job not found!")
    write_jobs(updated_jobs)
    return {"message": "✅ Job removed successfully!"}


# Send Email

@app.post("/send-email")
async def send_email(
    name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    message: str = Form(...),
    recipientEmail: str = Form(...),
    file: UploadFile = File(None)
):
    try:
        msg = EmailMessage()
        msg["Subject"] = "New Application"
        msg["From"] = email
        msg["To"] = recipientEmail

        msg.set_content(f"""
        Name: {name}
        Email: {email}
        Phone: {phone}
        Message: {message}
        """)

        # ✅ Read file content properly (Fix for .buffer error)
        if file:
            file_content = await file.read()
            msg.add_attachment(
                file_content,
                maintype="application",
                subtype="octet-stream",
                filename=file.filename
            )

        # ✅ Send using Gmail SMTP with App Password
        with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
            smtp.starttls()
            smtp.login(os.getenv("BUSINESS_EMAIL"),
                       os.getenv("BUSINESS_PASSWORD"))
            smtp.send_message(msg)

        return {"message": "✅ Email sent successfully!"}

    except Exception as e:
        print("❌ EMAIL ERROR:", e)
        raise HTTPException(status_code=500, detail=f"Email failed: {str(e)}")

# Run the app directly
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("inspirit:app", host="0.0.0.0", port=8000, reload=True)
