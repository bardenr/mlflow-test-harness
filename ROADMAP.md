# MLflow Test Harness Development Roadmap

This roadmap outlines the development plan for creating a multi-layered test suite for MLflow. Work will be completed in small, incremental chunks to maintain clarity and ensure each piece is tested before moving forward.

---

## Phase 1: MLflow Installation & Dependency Management ✅

Goal: Enable developers to easily install MLflow as an editable dependency from a local GitHub repository.

### Tasks

- [x] Add MLflow as an optional dependency in `pyproject.toml`
- [x] Create invoke task `install-mlflow` to handle editable install
  - [x] Accept `--mlflow-path` argument (with sensible default like `../mlflow`)
  - [x] Validate that the path exists and contains MLflow
  - [x] Run `pip install -e <path>` to install MLflow in editable mode
- [x] Add documentation to README.md explaining MLflow installation
- [x] Test the installation task manually
- [x] Create invoke task `uninstall-mlflow` for cleanup

---

## Phase 2: Test Configuration & Scopes

Goal: Set up different test scopes (unit, integration, server) with proper configuration.

### Tasks

- [ ] Create test directory structure
  - [ ] `tests/unit/` - Direct API import tests
  - [ ] `tests/server/` - MLflow server HTTP API tests
  - [ ] `tests/integration/` - Full integration tests with test service
- [ ] Add pytest configuration in `pyproject.toml`
  - [ ] Configure test discovery paths
  - [ ] Add markers for test scopes (unit, server, integration)
  - [ ] Set up pytest plugins
- [ ] Add `pytest-docker` to dev dependencies
- [ ] Create pytest fixtures for different test scopes
  - [ ] Create `tests/conftest.py` with shared fixtures
  - [ ] Add fixture for direct MLflow API access
  - [ ] Add fixture for MLflow server URL (localhost assumption)
- [ ] Create invoke tasks for running different test scopes
  - [ ] `invoke test-unit` - Run unit tests only
  - [ ] `invoke test-server` - Run server tests (assumes localhost MLflow)
  - [ ] `invoke test-integration` - Run integration tests
  - [ ] Update existing `invoke test` to run appropriate subset
- [ ] Add example test files for each scope
  - [ ] `tests/unit/test_mlflow_api.py` - Basic import test
  - [ ] `tests/server/test_mlflow_http.py` - Basic HTTP test
  - [ ] `tests/integration/test_integration.py` - Placeholder integration test

---

## Phase 3: Docker Infrastructure for Integration Testing

Goal: Create Docker infrastructure to run MLflow and test services in isolated containers.

### 3.1: MLflow Dockerfile

- [ ] Create `docker/mlflow/Dockerfile`
  - [ ] Set up base Python image
  - [ ] Add ARG for MLflow source path
  - [ ] Copy MLflow source into image
  - [ ] Install MLflow from local source
  - [ ] Configure database backend (SQLite initially)
  - [ ] Set up entrypoint for MLflow server
- [ ] Create `.dockerignore` for MLflow context
- [ ] Test building MLflow image manually
  - [ ] Document build command in README
  - [ ] Verify MLflow server starts correctly

### 3.2: Test Service Dockerfile

- [ ] Create `docker/test-service/Dockerfile`
  - [ ] Set up base Python image
  - [ ] Copy test harness source
  - [ ] Install test harness with dev dependencies
  - [ ] Set up entrypoint for test runner
- [ ] Test building test-service image manually

### 3.3: Docker Compose Configuration

- [ ] Create `docker-compose.yml` for integration tests
  - [ ] Define MLflow service
    - [ ] Configure build context with relative path
    - [ ] Set up database backend (PostgreSQL or MySQL)
    - [ ] Configure environment variables
    - [ ] Expose MLflow port
  - [ ] Define database service (if not using SQLite)
    - [ ] Configure persistent volume
    - [ ] Set up database initialization
  - [ ] Define test-service
    - [ ] Configure build context
    - [ ] Link to MLflow service
    - [ ] Set up environment variables (MLflow URL)
  - [ ] Configure shared network
- [ ] Create `.env.example` for Docker environment variables
- [ ] Test docker-compose setup manually
  - [ ] `docker-compose up` to start services
  - [ ] Verify MLflow is accessible from test service
  - [ ] `docker-compose down` to clean up

### 3.4: Docker Integration with Pytest

- [ ] Configure `pytest-docker` in `tests/conftest.py`
  - [ ] Add docker-compose file fixture
  - [ ] Add fixture to get MLflow URL from container
  - [ ] Add fixture to wait for MLflow server readiness
  - [ ] Add fixture for test service container
- [ ] Create invoke task `test-integration-docker`
  - [ ] Start docker-compose services
  - [ ] Run integration tests against containers
  - [ ] Clean up containers after tests
- [ ] Update integration test examples to use docker fixtures
- [ ] Test full docker integration flow

### 3.5: Documentation & Developer Experience

- [ ] Add Docker setup instructions to README
  - [ ] Prerequisites (Docker, docker-compose)
  - [ ] Building images
  - [ ] Running tests with Docker
- [ ] Create `docker/README.md` with detailed Docker documentation
- [ ] Add invoke task `docker-build` to build all images
- [ ] Add invoke task `docker-clean` to remove images and volumes
- [ ] Document common troubleshooting scenarios

---

## Future Enhancements (Post-MVP)

These items are not required for the initial implementation but may be valuable later:

- [ ] Add support for different database backends (MySQL, PostgreSQL)
- [ ] Create fixtures for pre-populated MLflow data
- [ ] Add performance testing suite
- [ ] Set up CI/CD pipeline integration
- [ ] Add support for testing against specific MLflow versions
- [ ] Create mock MLflow server for faster unit tests
- [ ] Add test reporting and metrics collection
- [ ] Support for parallel test execution
- [ ] Add test data generators and factories

---

## Notes

- Each phase builds on the previous one
- Mark items complete only after testing
- Keep commits small and focused on individual tasks
- Update this roadmap as requirements evolve
- Phase 1 and 2 don't require Docker, allowing faster initial development
