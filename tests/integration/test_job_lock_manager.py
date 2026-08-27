import platform
import time
from unittest import mock

import pytest
from sqlalchemy import Engine, create_engine, select, update
from sqlalchemy.orm import Query
from testcontainers.mssql import SqlServerContainer
from testcontainers.mysql import MySqlContainer
from testcontainers.postgres import PostgresContainer

from mlflow.server.jobs.lock_manager import JobLock, JobLockManager
from mlflow.store.db.db_types import MSSQL, MYSQL, POSTGRES
from mlflow.store.db.utils import get_current_time_millis_expression
from mlflow.store.jobs.abstract_store import JobUpdateStatus
from mlflow.store.jobs.sqlalchemy_store import SqlAlchemyJobStore
from mlflow.store.tracking.dbmodels.models import SqlJobLock, SqlSchedulerLease

SKIP_MSSQL = platform.machine() == "arm64"


@pytest.fixture(scope="module")
def mssql_engine() -> Engine:

    if SKIP_MSSQL:
        pytest.skip("MSSQL test unavailable on arm64 platforms")

    with SqlServerContainer().with_kwargs(platform="linux/amd64") as container:
        yield create_engine(container.get_connection_url())


@pytest.fixture(scope="module")
def mysql_engine() -> Engine:

    dialect = "pymysql"
    command = "--log-bin-trust-function-creators=1"
    with MySqlContainer(dialect=dialect, command=command) as container:
        yield create_engine(container.get_connection_url())


@pytest.fixture(scope="module")
def postgres_engine() -> Engine:

    with PostgresContainer() as container:
        yield create_engine(container.get_connection_url())


@pytest.mark.parametrize(
    ("db_type", "db_engine_fixture"),
    [
        (MSSQL, mssql_engine.__name__),
        (MYSQL, mysql_engine.__name__),
        (POSTGRES, postgres_engine.__name__),
    ],
    ids=[MSSQL, MYSQL, POSTGRES],
)
def test_acquire_scheduler_lease_returns_none_on_concurrent_insert_race_mock(
    request: pytest.FixtureRequest, db_type: str, db_engine_fixture: str
) -> None:

    db_engine: Engine = request.getfixturevalue(db_engine_fixture)
    connection_url = db_engine.url.render_as_string(hide_password=False)
    job_store = SqlAlchemyJobStore(connection_url)
    lock_mgr = JobLockManager(job_store)

    assert lock_mgr.acquire_scheduler_lease("scheduler", ttl_seconds=60) is not None

    # Mock only one_or_none to return None, simulating the race gap where
    # another replica committed after our SELECT but before our INSERT
    with mock.patch.object(Query, "one_or_none", return_value=None) as mock_one_or_none:
        assert lock_mgr.acquire_scheduler_lease("scheduler", ttl_seconds=60) is None
        mock_one_or_none.assert_called_once()


@pytest.mark.parametrize(
    ("db_type", "db_engine_fixture"),
    [
        (MSSQL, mssql_engine.__name__),
        (MYSQL, mysql_engine.__name__),
        (POSTGRES, postgres_engine.__name__),
    ],
    ids=[MSSQL, MYSQL, POSTGRES],
)
def test_get_current_time_millis_expression_millisecond_precision(
    request: pytest.FixtureRequest, db_type: str, db_engine_fixture: str
) -> None:

    db_engine: Engine = request.getfixturevalue(db_engine_fixture)
    db_now = get_current_time_millis_expression(db_type=db_type)

    with db_engine.connect() as connection:
        before = connection.execute(select(db_now)).scalar()

    time.sleep(0.002)
    with db_engine.connect() as connection:
        result = connection.execute(select(db_now)).scalar()

    time.sleep(0.002)
    with db_engine.connect() as connection:
        after = connection.execute(select(db_now)).scalar()

    assert before < result < after


@pytest.mark.parametrize(
    ("db_type", "db_engine_fixture"),
    [
        (MSSQL, mssql_engine.__name__),
        (MYSQL, mysql_engine.__name__),
        (POSTGRES, postgres_engine.__name__),
    ],
    ids=[MSSQL, MYSQL, POSTGRES],
)
def test_exclusive_lock_joined_update_uses_holding_job_status(
    request: pytest.FixtureRequest, db_type: str, db_engine_fixture: str
) -> None:

    db_engine: Engine = request.getfixturevalue(db_engine_fixture)
    connection_url = db_engine.url.render_as_string(hide_password=False)
    job_store = SqlAlchemyJobStore(connection_url)
    lock_mgr = JobLockManager(job_store)

    holding_job = job_store.create_job(job_name="status-holder", params="{}", timeout=60.0)
    assert job_store.claim_job(holding_job.job_id) == JobUpdateStatus.APPLIED

    original_lock = lock_mgr.acquire_exclusive_lock("status-update", holding_job.job_id)
    assert isinstance(original_lock, JobLock)

    # The requesting job is PENDING, but the joined predicate must evaluate the RUNNING job
    # that currently holds the lock, so the update is refused.
    requesting_job = job_store.create_job(job_name="status-requester", params="{}", timeout=60.0)
    assert lock_mgr.acquire_exclusive_lock("status-update", requesting_job.job_id) is None

    job_store.finish_job(holding_job.job_id, "holder finished")

    reacquired_lock = lock_mgr.acquire_exclusive_lock("status-update", requesting_job.job_id)
    assert isinstance(reacquired_lock, JobLock)
    assert reacquired_lock.job_id == requesting_job.job_id
    assert reacquired_lock.acquired_at >= original_lock.acquired_at

    with lock_mgr._session_maker(read_only=True) as session:
        lock_row = session.query(SqlJobLock).filter_by(lock_key="status-update").one()
        assert lock_row.job_id == requesting_job.job_id


@pytest.mark.parametrize(
    ("db_type", "db_engine_fixture"),
    [
        (MSSQL, mssql_engine.__name__),
        (MYSQL, mysql_engine.__name__),
        (POSTGRES, postgres_engine.__name__),
    ],
    ids=[MSSQL, MYSQL, POSTGRES],
)
def test_exclusive_lock_joined_update_replaces_timed_out_running_job(
    request: pytest.FixtureRequest, db_type: str, db_engine_fixture: str
) -> None:

    db_engine: Engine = request.getfixturevalue(db_engine_fixture)
    connection_url = db_engine.url.render_as_string(hide_password=False)
    job_store = SqlAlchemyJobStore(connection_url)
    lock_mgr = JobLockManager(job_store)

    holding_job = job_store.create_job(job_name="timeout-holder", params="{}", timeout=60.0)
    assert job_store.claim_job(holding_job.job_id) == JobUpdateStatus.APPLIED

    original_lock = lock_mgr.acquire_exclusive_lock("timeout-update", holding_job.job_id)
    assert isinstance(original_lock, JobLock)

    # Age the lock beyond 115% of the holding job's timeout without relying on wall-clock sleeps.
    with lock_mgr._session_maker(read_only=False) as session:
        result = session.execute(
            update(SqlJobLock)
            .filter(SqlJobLock.lock_key == "timeout-update")
            .values(acquired_at=original_lock.acquired_at - 70_000)
        )
        assert result.rowcount == 1

    requesting_job = job_store.create_job(job_name="timeout-requester", params="{}", timeout=60.0)
    reacquired_lock = lock_mgr.acquire_exclusive_lock("timeout-update", requesting_job.job_id)

    assert isinstance(reacquired_lock, JobLock)
    assert reacquired_lock.job_id == requesting_job.job_id
    assert reacquired_lock.acquired_at >= original_lock.acquired_at

    with lock_mgr._session_maker(read_only=True) as session:
        lock_row = session.query(SqlJobLock).filter_by(lock_key="timeout-update").one()
        assert lock_row.job_id == requesting_job.job_id


@pytest.mark.parametrize(
    ("db_type", "db_engine_fixture"),
    [
        (MSSQL, mssql_engine.__name__),
        (MYSQL, mysql_engine.__name__),
        (POSTGRES, postgres_engine.__name__),
    ],
    ids=[MSSQL, MYSQL, POSTGRES],
)
def test_job_lock_manager_smoke_test(request: pytest.FixtureRequest, db_type: str, db_engine_fixture: str) -> None:

    db_engine: Engine = request.getfixturevalue(db_engine_fixture)
    connection_url = db_engine.url.render_as_string(hide_password=False)
    job_store = SqlAlchemyJobStore(connection_url)
    lock_mgr = JobLockManager(job_store)

    lease_key = "scheduler-lease"
    ttl = 100

    # 1. Replica A acquires the lease at.
    lease_a_1 = lock_mgr.acquire_scheduler_lease(lease_key, ttl_seconds=ttl)
    assert lease_a_1 is not None
    assert lease_a_1.lease_key == lease_key
    assert lease_a_1.ttl_seconds == ttl

    # 2. Replica A renews within TTL (sleep prevents sub millisecond renewal)
    time.sleep(0.002)
    lease_a_2 = lock_mgr.renew_scheduler_lease(lease_a_1, ttl_seconds=ttl)
    assert lease_a_2.lease_key == lease_key
    assert lease_a_2.ttl_seconds == ttl
    assert lease_a_2.ttl_seconds == lease_a_1.ttl_seconds
    assert lease_a_2.acquired_at != lease_a_1.acquired_at

    # 3. Replica B attempts acquires the lease and is denied.
    assert lock_mgr.acquire_scheduler_lease(lease_key, ttl_seconds=ttl) is None

    # 4. Replica A attempts renewal with its old lease and fails
    assert lock_mgr.renew_scheduler_lease(lease_a_1, ttl_seconds=ttl) is None

    # 6. Verify final DB state matches Replica B's lease.
    with lock_mgr._session_maker(read_only=True) as session:
        row = session.query(SqlSchedulerLease).filter(SqlSchedulerLease.lease_key == lease_key).one()
        assert row.lease_key == lease_a_2.lease_key
        assert row.acquired_at == lease_a_2.acquired_at
        assert row.ttl_seconds == lease_a_2.ttl_seconds
