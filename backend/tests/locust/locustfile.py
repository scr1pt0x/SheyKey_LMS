"""
Load test: simulates concurrent users for Islamic Finance LMS.
Usage:
  locust -f backend/tests/locust/locustfile.py --host=http://localhost:8000
  locust -f backend/tests/locust/locustfile.py --host=http://localhost:8000 --headless -u 50 -r 5 --run-time 60s

Simulates:
  - 2000 clients
  - 6000 deals
  - Concurrent manager/SB/director sessions
"""
import random
from locust import HttpUser, TaskSet, between, task


class ManagerTasks(TaskSet):
    def on_start(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"phone": "+79000000002", "password": "Manager12345!"},
        )
        if resp.status_code != 200:
            self.interrupt()

    @task(3)
    def list_clients(self):
        self.client.get(
            "/api/clients",
            params={"limit": 20, "offset": random.randint(0, 50)},
            name="/api/clients (list)",
        )

    @task(3)
    def list_deals(self):
        self.client.get(
            "/api/deals",
            params={"limit": 20, "offset": random.randint(0, 100)},
            name="/api/deals (list)",
        )

    @task(1)
    def calendar_today(self):
        self.client.get("/api/calendar/today")

    @task(1)
    def calendar_week(self):
        self.client.get("/api/calendar/week")


class SbTasks(TaskSet):
    def on_start(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"phone": "+79000000003", "password": "SB12345!"},
        )
        if resp.status_code != 200:
            self.interrupt()

    @task(3)
    def list_cases(self):
        self.client.get(
            "/api/sb/cases",
            params={"limit": 20, "offset": random.randint(0, 30)},
            name="/api/sb/cases (list)",
        )

    @task(1)
    def sb_dashboard(self):
        self.client.get("/api/sb/dashboard")


class DirectorTasks(TaskSet):
    def on_start(self):
        resp = self.client.post(
            "/api/auth/login",
            json={"phone": "+79000000001", "password": "Admin12345!"},
        )
        if resp.status_code != 200:
            self.interrupt()

    @task(2)
    def director_dashboard(self):
        self.client.get("/api/director/dashboard")

    @task(1)
    def analytics_portfolio(self):
        self.client.get("/api/director/analytics/portfolio")

    @task(1)
    def analytics_issuance(self):
        self.client.get("/api/director/analytics/issuance", params={"months": 12})

    @task(1)
    def approval_queue(self):
        self.client.get("/api/director/approval/deals")


class ManagerUser(HttpUser):
    tasks = [ManagerTasks]
    wait_time = between(1, 3)
    weight = 3


class SbUser(HttpUser):
    tasks = [SbTasks]
    wait_time = between(1, 4)
    weight = 2


class DirectorUser(HttpUser):
    tasks = [DirectorTasks]
    wait_time = between(2, 5)
    weight = 1
