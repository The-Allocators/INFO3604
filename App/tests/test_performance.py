from locust import HttpUser, task, between

class PerformanceTests(HttpUser):
    wait_time = between(1, 2)

    def on_start(self):
        # Login as admin and volunteer to get tokens
        admin_response = self.client.post('/api/login', json={
            "username": "a",
            "password": "123"
        })
        if admin_response.status_code == 200:
            self.admin_token = admin_response.json().get('access_token')
        else:
            self.admin_token = None

        volunteer_response = self.client.post('/api/login', json={
            "username": "816031003",
            "password": "123"
        })
        if volunteer_response.status_code == 200:
            self.volunteer_token = volunteer_response.json().get('access_token')
        else:
            self.volunteer_token = None

    @task
    def test_homepage(self):
        response = self.client.get("/")
        assert response.elapsed.total_seconds() < 15, f"Homepage took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_authentication_admin(self):
        response = self.client.post('/api/login', json={
            "username": "a",
            "password": "123"
        })
        assert response.elapsed.total_seconds() < 15, f"Authentication took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_schedule_generation(self):
        headers = {}
        if self.admin_token:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.client.post("/api/schedule/generate", json={}, headers=headers)
        assert response.elapsed.total_seconds() < 15, f"Schedule generation took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_schedule(self):
        headers = {}
        if self.admin_token:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.client.get("/api/schedule/details", headers=headers)
        assert response.elapsed.total_seconds() < 15, f"Schedule retrieval took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_user_profile(self):
        headers = {}
        if self.volunteer_token:
            headers = {"Authorization": f"Bearer {self.volunteer_token}"}
        response = self.client.get("/volunteer/profile", headers=headers)
        assert response.elapsed.total_seconds() < 15, f"User profile retrieval took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_create_request(self):
        headers = {}
        if self.volunteer_token:
            headers = {"Authorization": f"Bearer {self.volunteer_token}"}
        response = self.client.post("/volunteer/submit_request", data={
            "shiftToChange": "1",
            "reasonForChange": "Performance test request",
            "proposedReplacement": ""
        }, headers=headers)
        assert response.elapsed.total_seconds() < 15, f"Request creation took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_list_requests(self):
        headers = {}
        if self.volunteer_token:
            headers = {"Authorization": f"Bearer {self.volunteer_token}"}
        response = self.client.get("/volunteer/requests", headers=headers)
        assert response.elapsed.total_seconds() < 15, f"Request listing took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_tracking_data(self):
        headers = {}
        if self.volunteer_token:
            headers = {"Authorization": f"Bearer {self.volunteer_token}"}
        response = self.client.get("/timeTracking", headers=headers)
        assert response.elapsed.total_seconds() < 15, f"Tracking data retrieval took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_admin_dashboard(self):
        headers = {}
        if self.admin_token:
            headers = {"Authorization": f"Bearer {self.admin_token}"}
        response = self.client.get("/admin/", headers=headers)
        assert response.elapsed.total_seconds() < 15, f"Admin dashboard took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_volunteer_dashboard(self):
        headers = {}
        if self.volunteer_token:
            headers = {"Authorization": f"Bearer {self.volunteer_token}"}
        response = self.client.get("/volunteer/dashboard", headers=headers)
        assert response.elapsed.total_seconds() < 15, f"Volunteer dashboard took too long to respond, response time: {response.elapsed.total_seconds()} seconds"

    @task
    def test_get_notifications(self):
        headers = {}
        if self.volunteer_token:
            headers = {"Authorization": f"Bearer {self.volunteer_token}"}
