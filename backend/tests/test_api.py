import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from uuid import uuid4
from datetime import datetime, timezone

from app.main import app
from app.core.config import get_settings
from app.core.database import get_db, Base
from app.models import Job, JobSource, CollectionRun, Classification, ClassificationUsage, SourceStatus
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool


# Use an in-memory SQLite async DB for fast unit/integration testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def test_db():

    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # Seed test data
        job1 = Job(
            id=uuid4(),
            title="Software Development Engineer Intern",
            company="Razorpay",
            description="Build scalable payment microservices in Python.",
            location="Bengaluru",
            city="Bengaluru",
            employment_type="Internship",
            experience_level="Internship",
            application_url="https://razorpay.com/jobs/1",
            source_name="Greenhouse:razorpay",
            role_category="Backend Development",
            skills=["Python", "FastAPI", "PostgreSQL"],
            is_remote=False,
            fingerprint="fp1_razorpay_sde_intern",
            posted_at=datetime(2026, 11, 19, 12, 0, 0, tzinfo=timezone.utc),
            status="active",
            classification_confidence=0.95,
            classification_status="classified",
        )
        job2 = Job(
            id=uuid4(),
            title="Frontend Developer Trainee",
            company="Freshworks",
            description="Work with React and TypeScript on our CRM product.",
            location="Chennai",
            city="Chennai",
            employment_type="Full-time",
            experience_level="Fresher",
            application_url="https://freshworks.com/jobs/2",
            source_name="Greenhouse:freshworks",
            role_category="Frontend Development",
            skills=["React", "TypeScript", "CSS"],
            is_remote=False,
            fingerprint="fp2_freshworks_frontend",
            posted_at=datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc),
            status="active",
            classification_confidence=0.91,
            classification_status="classified",
        )
        job3 = Job(
            id=uuid4(),
            title="Junior Cloud Engineer",
            company="Hasura",
            description="Infrastructure as code, Docker, Kubernetes and Terraform.",
            location="Remote",
            city="Remote",
            employment_type="Full-time",
            experience_level="Entry-level",
            application_url="https://hasura.io/jobs/3",
            source_name="Remotive",
            role_category="DevOps / Cloud",
            skills=["Docker", "Kubernetes", "AWS"],
            is_remote=True,
            fingerprint="fp3_hasura_devops",
            status="active",
            classification_confidence=0.88,
            classification_status="classified",
        )
        source_stat = SourceStatus(
            id=uuid4(),
            source_name="Remotive",
            is_enabled=True,
            total_jobs_collected=10,
            total_runs=1,
            total_failures=0,
        )
        run = CollectionRun(
            id=uuid4(),
            status="completed",
            trigger_type="manual",
            total_fetched=10,
            total_new=3,
            total_updated=0,
            total_duplicates=0,
            total_classified=3,
            total_failed=0,
            total_errors=0,
            completed_at=datetime.now(timezone.utc),
        )
        session.add_all([job1, job2, job3, source_stat, run])
        await session.commit()

        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db):

    async def override_get_db():
        yield test_db

    from app.api.deps import get_session
    app.dependency_overrides[get_session] = override_get_db
    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_root_endpoint(client):
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "LaunchBoard API" in data["name"]


@pytest.mark.asyncio
async def test_get_roles(client):
    response = await client.get("/api/roles")
    assert response.status_code == 200
    roles = response.json()
    assert len(roles) >= 3
    role_names = [r["role_category"] for r in roles]
    assert "Backend Development" in role_names
    assert "Frontend Development" in role_names


@pytest.mark.asyncio
async def test_get_cities(client):
    response = await client.get("/api/cities")
    assert response.status_code == 200
    cities = response.json()
    assert len(cities) >= 2
    city_names = [c["city"] for c in cities]
    assert "Bengaluru" in city_names or "Chennai" in city_names


@pytest.mark.asyncio
async def test_get_stats(client):
    response = await client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["total_active_jobs"] == 3
    assert data["total_remote_jobs"] == 1
    assert data["total_companies"] == 3


@pytest.mark.asyncio
async def test_search_jobs(client):
    # Search for 'python'
    response = await client.get("/api/jobs?q=python")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["jobs"][0]["company"] == "Razorpay"


@pytest.mark.asyncio
async def test_filter_remote_jobs(client):
    response = await client.get("/api/jobs?is_remote=true")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["jobs"][0]["is_remote"] is True


@pytest.mark.asyncio
async def test_filter_by_role(client):
    response = await client.get("/api/jobs?role_category=Frontend Development")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["jobs"][0]["company"] == "Freshworks"


@pytest.mark.asyncio
async def test_admin_auth_required(client):
    # Missing admin key should be 403
    response = await client.post("/api/admin/refresh")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_dashboard_with_key(client):
    settings = get_settings()
    headers = {"X-Admin-API-Key": settings.ADMIN_API_KEY}
    response = await client.get("/api/admin/dashboard", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs_collected" in data
    assert "cost_report" in data


@pytest.mark.asyncio
async def test_default_sort_newest_posted_first(client):
    """Requirement 11: Most recently posted jobs appear at the top by default."""
    response = await client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    # job1 posted today (1 hour ago) must appear before job2 posted 2 days ago
    assert data["jobs"][0]["company"] == "Razorpay"
    assert data["jobs"][1]["company"] == "Freshworks"


@pytest.mark.asyncio
async def test_sort_nulls_last_for_unknown_posting_date(client):
    """Requirement 11: Jobs with missing posted_at appear after dated jobs."""
    response = await client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    # job3 has posted_at = None, so it must be last
    assert data["jobs"][2]["company"] == "Hasura"
    assert data["jobs"][2]["posted_at"] is None


@pytest.mark.asyncio
async def test_sorting_preserved_across_filtering_and_pagination(client):
    """Requirement 11: Filtering preserves newest-first ordering."""
    # Filter with employment_type
    response = await client.get("/api/jobs?employment_type=Full-time")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    # Freshworks (dated) must come before Hasura (undated)
    assert data["jobs"][0]["company"] == "Freshworks"
    assert data["jobs"][1]["company"] == "Hasura"


@pytest.mark.asyncio
async def test_refreshing_existing_job_does_not_change_posted_at(client, test_db):
    """Requirement 11: Refreshing an existing job does not make it appear newer."""
    from sqlalchemy import select, update
    from app.models.job import Job

    # Check job2 (Freshworks) posted_at in test_db
    result = await test_db.execute(select(Job).where(Job.company == "Freshworks"))
    job2 = result.scalar_one()
    initial_posted_at = job2.posted_at
    assert initial_posted_at == datetime(2026, 11, 17, 12, 0, 0, tzinfo=timezone.utc)

    # Simulate job refresh: update last_verified_at to now
    now = datetime.now(timezone.utc)
    await test_db.execute(
        update(Job).where(Job.id == job2.id).values(last_verified_at=now)
    )
    await test_db.commit()

    # Query API again: Razorpay must still be #1 because posted_at didn't change
    response = await client.get("/api/jobs")
    assert response.status_code == 200
    data = response.json()
    assert data["jobs"][0]["company"] == "Razorpay"
    assert data["jobs"][1]["company"] == "Freshworks"
    assert data["jobs"][1]["posted_at"] == initial_posted_at.isoformat().replace("+00:00", "Z")


def test_render_database_url_normalization():
    """Verify DATABASE_URL normalizes Render postgres:// and sslmode query parameter."""
    from app.core.config import Settings

    # Case 1: Render postgres:// without sslmode
    s1 = Settings(DATABASE_URL="postgres://render_user:pass123@dpg-abc:5432/launchboard")
    assert s1.DATABASE_URL == "postgresql+asyncpg://render_user:pass123@dpg-abc:5432/launchboard"

    # Case 2: Render postgres:// with sslmode=require
    s2 = Settings(DATABASE_URL="postgres://render_user:pass123@dpg-abc:5432/launchboard?sslmode=require")
    assert s2.DATABASE_URL == "postgresql+asyncpg://render_user:pass123@dpg-abc:5432/launchboard?ssl=require"

    # Case 3: Standard postgresql:// with sslmode=prefer
    s3 = Settings(DATABASE_URL="postgresql://user:pass@localhost:5432/mydb?sslmode=prefer")
    assert s3.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/mydb?ssl=prefer"

    # Case 4: Standard postgresql+asyncpg:// (already correct)
    s4 = Settings(DATABASE_URL="postgresql+asyncpg://user:pass@localhost:5432/mydb")
    assert s4.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/mydb"


def test_enable_scheduler_setting():
    """Verify ENABLE_SCHEDULER setting defaults to True and can be disabled."""
    from app.core.config import Settings
    s_default = Settings()
    assert s_default.ENABLE_SCHEDULER is True

    s_disabled = Settings(ENABLE_SCHEDULER=False)
    assert s_disabled.ENABLE_SCHEDULER is False


@pytest.mark.asyncio
async def test_cors_vercel_preview_domains(client):
    """Verify Vercel preview domains are accepted by CORS regex."""
    headers = {
        "Origin": "https://launchboard-git-preview-myuser.vercel.app",
        "Access-Control-Request-Method": "GET",
    }
    response = await client.options("/api/stats", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://launchboard-git-preview-myuser.vercel.app"



