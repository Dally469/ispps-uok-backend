"""Analytics dashboard summary."""
from __future__ import annotations

from tests.conftest import DSA_COURSE_ID, SCHOOL_ID


async def test_summary_requires_school(client, admin_headers):
    # admin token includes a school_id in conftest so this works
    r = await client.get("/api/analytics/summary", headers=admin_headers)
    assert r.status_code == 200, r.text


async def test_summary_shape(client, admin_headers):
    r = await client.get(
        f"/api/analytics/summary?school_id={SCHOOL_ID}", headers=admin_headers
    )
    assert r.status_code == 200
    body = r.json()
    expected = {
        "totalStudents",
        "totalCourses",
        "averageGPA",
        "atRiskCount",
        "attendanceRate",
        "riskDistribution",
        "gradeDistribution",
        "departmentPerformance",
        "recentPredictions",
    }
    assert expected <= set(body)
    assert body["totalStudents"] >= 1
    assert body["totalCourses"] >= 1
    assert isinstance(body["riskDistribution"], dict)
    assert set(body["riskDistribution"]) == {"low", "medium", "high", "critical"}


async def test_summary_grade_distribution_buckets(client, admin_headers):
    r = await client.get(
        f"/api/analytics/summary?school_id={SCHOOL_ID}", headers=admin_headers
    )
    body = r.json()
    grades = {row["grade"] for row in body["gradeDistribution"]}
    assert grades == {"A", "B", "C", "D", "F"}


async def test_summary_filter_by_course(client, admin_headers):
    r = await client.get(
        f"/api/analytics/summary?school_id={SCHOOL_ID}&course_id={DSA_COURSE_ID}",
        headers=admin_headers,
    )
    assert r.status_code == 200
    # totalCourses should narrow to 1
    assert r.json()["totalCourses"] == 1


async def test_lecturer_summary_scoped_to_own_courses(client, lecturer_headers):
    r = await client.get(
        f"/api/analytics/summary?school_id={SCHOOL_ID}", headers=lecturer_headers
    )
    assert r.status_code == 200
    body = r.json()
    # Dr. Silva owns 2 courses
    assert body["totalCourses"] == 2
