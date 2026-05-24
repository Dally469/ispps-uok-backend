from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    auth,
    students,
    attendance,
    courses,
    predictions,
    analytics,
    insights,
    admin,
    reports,
    imports,
    grades,
)

app = FastAPI(title="ISPPS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(attendance.router)
app.include_router(courses.router)
app.include_router(predictions.router)
app.include_router(analytics.router)
app.include_router(insights.router)
app.include_router(admin.router)
app.include_router(reports.router)
app.include_router(imports.router)
app.include_router(grades.router)

@app.get("/api/health")
async def health():
    return {"status": "ok"}
