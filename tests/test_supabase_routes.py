import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main
from main import app, HARI_USERNAME, HARI_PASSWORD


class TestSupabaseInvoiceRoutes(unittest.TestCase):
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

    def test_get_invoices_success(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_order = MagicMock()
        mock_select.order.return_value = mock_order

        # Mock query return data with real Supabase columns
        mock_execute = MagicMock()
        mock_execute.data = [
            {"id": 1, "invoice_id": "1723659000000", "file_name": "Invoice #101", "html_data": "<div>Test 1</div>", "created_at": "2026-08-14T00:00:00Z"},
            {"id": 2, "invoice_id": "1723658000000", "file_name": "Invoice #100", "html_data": "<div>Test 0</div>", "created_at": "2026-08-13T00:00:00Z"}
        ]
        mock_order.execute.return_value = mock_execute

        response = self.client.get("/get-invoices")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["id"], "1723659000000")
        self.assertEqual(data[0]["name"], "Invoice #101")
        self.assertEqual(data[0]["data"], "<div>Test 1</div>")

    def test_get_single_invoice_found(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq

        mock_execute = MagicMock()
        mock_execute.data = [{"id": 1, "invoice_id": "1723659000000", "file_name": "Invoice #101", "html_data": "<div>Content</div>"}]
        mock_eq.execute.return_value = mock_execute

        response = self.client.get("/get-invoice/1723659000000")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "1723659000000")
        self.assertEqual(data["name"], "Invoice #101")
        self.assertEqual(data["data"], "<div>Content</div>")

    def test_get_single_invoice_not_found(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_eq = MagicMock()
        mock_select.eq.return_value = mock_eq

        mock_execute = MagicMock()
        mock_execute.data = []
        mock_eq.execute.return_value = mock_execute

        response = self.client.get("/get-invoice/999999")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["id"], "999999")
        self.assertEqual(data["name"], "")
        self.assertEqual(data["data"], "")

    def test_save_invoice(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_insert = MagicMock()
        mock_table.insert.return_value = mock_insert
        mock_execute = MagicMock()
        mock_execute.data = [{"id": 1, "invoice_id": "1723659000000", "file_name": "New Invoice 2026", "html_data": "<table><tr><td>Item</td></tr></table>"}]
        mock_insert.execute.return_value = mock_execute

        payload = {"name": "New Invoice 2026", "data": "<table><tr><td>Item</td></tr></table>", "invoice_id": "1723659000000"}
        response = self.client.post("/save", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["message"], "Invoice saved")
        self.assertEqual(data["invoice_id"], "1723659000000")
        mock_table.insert.assert_called_once_with({
            "invoice_id": "1723659000000",
            "file_name": "New Invoice 2026",
            "html_data": "<table><tr><td>Item</td></tr></table>"
        })

    def test_update_invoice(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_update = MagicMock()
        self.mock_supabase.table.return_value.update.return_value = mock_update
        mock_eq = MagicMock()
        mock_update.eq.return_value = mock_eq

        payload = {"id": "1723659000000", "name": "Updated Name", "data": "<div>Updated HTML</div>"}
        response = self.client.post("/update-invoice", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["message"], "Invoice updated")
        mock_table.update.assert_called_once_with({
            "file_name": "Updated Name",
            "html_data": "<div>Updated HTML</div>"
        })

    def test_rename_invoice(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_update = MagicMock()
        self.mock_supabase.table.return_value.update.return_value = mock_update
        mock_eq = MagicMock()
        mock_update.eq.return_value = mock_eq

        payload = {"old_id": "1723659000000", "new_id": "Renamed Invoice #102"}
        response = self.client.post("/rename-invoice", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["message"], "Renamed")
        mock_table.update.assert_called_once_with({
            "file_name": "Renamed Invoice #102"
        })

    def test_delete_invoice(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_delete = MagicMock()
        mock_table.delete.return_value = mock_delete
        mock_eq = MagicMock()
        mock_delete.eq.return_value = mock_eq

        payload = {"id": "1723659000000"}
        response = self.client.post("/delete-invoice", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["message"], "Deleted")
        mock_table.delete.assert_called_once()

    def test_database_error_returns_500(self):
        self.login()
        mock_table = MagicMock()
        self.mock_supabase.table.return_value = mock_table
        mock_select = MagicMock()
        mock_table.select.return_value = mock_select
        mock_select.order.side_effect = Exception("Supabase connection timeout")

        response = self.client.get("/get-invoices")
        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        self.assertIn("error", data)
        self.assertIn("Supabase connection timeout", data["error"])


if __name__ == "__main__":
    unittest.main()
