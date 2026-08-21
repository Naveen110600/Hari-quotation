import os
import sys
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from main import app, HARI_USERNAME, HARI_PASSWORD


class TestValidityDatePersistence(unittest.TestCase):
    def setUp(self):
        app.config["TESTING"] = True
        app.config["WTF_CSRF_ENABLED"] = False
        self.client = app.test_client()
        self.mock_supabase = MagicMock()
        main.supabase = self.mock_supabase

    def login(self):
        return self.client.post(
            "/login",
            data={"username": HARI_USERNAME, "password": HARI_PASSWORD},
            follow_redirects=True
        )

    def test_index_html_has_validity_functions(self):
        self.login()
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)
        self.assertIn("syncValidityDate", html)
        self.assertIn("restoreValidityDate", html)
        self.assertIn("validity-date-input", html)
        self.assertIn("validity-date-text", html)

    def test_save_and_retrieve_invoice_with_validity_date(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_insert.execute.return_value = MagicMock(data=[{"id": 1, "invoice_id": "12345"}])

        # Simulate saved HTML that has value attribute set
        sample_html = (
            '<div id="a4" class="a4-portrait">'
            '<input type="text" id="validity-date-input" value="19/08/2026">'
            '<span id="validity-date-text" class="validity-date-text">19/08/2026</span>'
            '</div>'
        )

        # 1. Save invoice
        res = self.client.post("/save", json={"name": "Invoice #101", "data": sample_html})
        self.assertEqual(res.status_code, 200)

        # 2. Mock get-invoice
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(
            data=[{"id": 1, "invoice_id": "12345", "file_name": "Invoice #101", "html_data": sample_html}]
        )

        res = self.client.get("/get-invoice/12345")
        self.assertEqual(res.status_code, 200)
        retrieved_data = res.get_json()["data"]
        self.assertIn('value="19/08/2026"', retrieved_data)
        self.assertIn('>19/08/2026</span>', retrieved_data)

    def test_update_invoice_with_new_validity_date(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_update = MagicMock()
        mock_table.update.return_value = mock_update
        mock_eq = MagicMock()
        mock_update.eq.return_value = mock_eq
        mock_eq.execute.return_value = MagicMock(data=[{"id": 1, "invoice_id": "12345"}])

        updated_html = (
            '<div id="a4" class="a4-portrait">'
            '<input type="text" id="validity-date-input" value="25/12/2026">'
            '<span id="validity-date-text" class="validity-date-text">25/12/2026</span>'
            '</div>'
        )

        res = self.client.post("/update-invoice", json={"id": "12345", "name": "Invoice #101", "data": updated_html})
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
