import os
import sys
import unittest

# Add app directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app, HARI_USERNAME, HARI_PASSWORD


class TestHariAppAuth(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()

    def test_unauthenticated_redirect(self):
        """1. Open the application unauthenticated -> redirects to login page"""
        response = self.client.get("/", follow_redirects=False)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.headers["Location"])

    def test_login_page_renders(self):
        """1. Login page displays properly with form and branding"""
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Hari App", content)
        self.assertIn("username", content.lower())
        self.assertIn("password", content.lower())
        self.assertIn("loginForm", content)

    def test_empty_credentials_rejected(self):
        """5. Empty username/password -> Validation shown"""
        response = self.client.post("/login", data={"username": "", "password": ""}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Please enter both username and password", content)

        # Empty password only
        response = self.client.post("/login", data={"username": "Hari", "password": ""}, follow_redirects=True)
        content = response.data.decode("utf-8")
        self.assertIn("Please enter both username and password", content)

    def test_wrong_username_rejected(self):
        """3. Wrong username -> Login rejected"""
        response = self.client.post("/login", data={"username": "WrongUser", "password": HARI_PASSWORD}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Invalid username or password", content)

    def test_wrong_password_rejected(self):
        """4. Wrong password -> Login rejected"""
        response = self.client.post("/login", data={"username": HARI_USERNAME, "password": "WrongPassword123"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        content = response.data.decode("utf-8")
        self.assertIn("Invalid username or password", content)

    def test_correct_login_and_session(self):
        """2 & 6. Correct username + correct password -> Main app opens & session persists across requests"""
        with self.client:
            response = self.client.post(
                "/login",
                data={"username": HARI_USERNAME, "password": HARI_PASSWORD},
                follow_redirects=False
            )
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.headers["Location"], "/")

            # Access index as authenticated user
            index_response = self.client.get("/")
            self.assertEqual(index_response.status_code, 200)
            index_content = index_response.data.decode("utf-8")
            self.assertIn("SRI TRADERS", index_content)
            self.assertIn("Logout", index_content)

            # Access API endpoints as authenticated user
            api_response = self.client.get("/get-invoices")
            self.assertEqual(api_response.status_code, 200)

    def test_api_unauthorized_when_not_logged_in(self):
        """8. Prevent unauthorized API access"""
        response = self.client.get("/get-invoices")
        self.assertEqual(response.status_code, 401)

        response = self.client.post("/save", json={"name": "test", "data": "<html></html>"})
        self.assertEqual(response.status_code, 401)

    def test_logout(self):
        """7. Logout -> Returns to login page and clears session"""
        with self.client:
            # First login
            self.client.post("/login", data={"username": HARI_USERNAME, "password": HARI_PASSWORD})
            # Check authenticated access
            self.assertEqual(self.client.get("/").status_code, 200)

            # Perform logout
            logout_response = self.client.get("/logout", follow_redirects=False)
            self.assertEqual(logout_response.status_code, 302)
            self.assertIn("/login", logout_response.headers["Location"])

            # Now access to index should redirect to login again
            subsequent_response = self.client.get("/", follow_redirects=False)
            self.assertEqual(subsequent_response.status_code, 302)
            self.assertIn("/login", subsequent_response.headers["Location"])


if __name__ == "__main__":
    unittest.main()
