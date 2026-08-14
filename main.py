import os
import sys
import time
import io
import webbrowser
import threading
from datetime import datetime, timezone

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file, session, redirect, url_for
from supabase import create_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

EXTRACTED_DIR = os.path.join(
    BASE_DIR,
    "extracted",
    "OldBilling.exe_extracted"
)

app = Flask(
    __name__,
    template_folder=os.path.join(EXTRACTED_DIR, "templates"),
    static_folder=os.path.join(EXTRACTED_DIR, "static")
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "sri-traders-hari-app-secure-session-key-2026")
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax"
)

HARI_USERNAME = os.environ.get("HARI_USERNAME", "Hari")
HARI_PASSWORD = os.environ.get("HARI_PASSWORD", "Uma@1999")

SUPABASE_URL = (os.environ.get("SUPABASE_URL") or "").strip()
SUPABASE_KEY = (os.environ.get("SUPABASE_KEY") or "").strip()

supabase = None


def get_supabase():
    global supabase
    if supabase is None:
        url = (os.environ.get("SUPABASE_URL") or SUPABASE_URL or "").strip()
        key = (os.environ.get("SUPABASE_KEY") or SUPABASE_KEY or "").strip()
        if url and key:
            try:
                supabase = create_client(url, key)
            except Exception as e:
                print("Error initializing Supabase client:", e)
    return supabase


def reset_supabase():
    global supabase
    supabase = None


def format_supabase_error(e):
    err_str = ""
    if hasattr(e, "json") and callable(e.json):
        try:
            err_dict = e.json()
            if isinstance(err_dict, dict) and "message" in err_dict:
                err_str = err_dict["message"]
        except Exception:
            pass
    if not err_str:
        if hasattr(e, "message") and e.message:
            err_str = str(e.message)
        elif hasattr(e, "args") and e.args:
            first_arg = e.args[0]
            if isinstance(first_arg, dict) and "message" in first_arg:
                err_str = first_arg["message"]
            else:
                err_str = str(first_arg)
        else:
            err_str = str(e)

    if "row-level security" in err_str.lower() or "rls" in err_str.lower():
        err_str += " (Supabase RLS Policy: The 'invoices' table is blocking write access. Disable RLS or add an INSERT policy for anon in Supabase, or provide the service_role key in .env)"
    return err_str


@app.before_request
def require_login():
    # Allow login route and static files without login
    if request.endpoint in ["login", "static"] or (request.path and request.path.startswith("/static/")):
        return None

    if not session.get("logged_in"):
        if request.is_json or request.path.startswith("/get-") or request.path in ["/save", "/update-invoice", "/rename-invoice", "/delete-invoice", "/pdf-action"]:
            return jsonify({"error": "Unauthorized"}), 401
        return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("index"))

    error = None
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if not username or not password:
            error = "Please enter both username and password"
        elif username == HARI_USERNAME and password == HARI_PASSWORD:
            session["logged_in"] = True
            session["username"] = username
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password"

    return render_template("login.html", error=error)


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get-invoices")
def get_invoices():
    db = get_supabase()
    if not db:
        return jsonify({"error": "Supabase client is not configured"}), 500

    try:
        response = db.table("invoices").select("id, invoice_id, file_name, html_data, created_at").order("id", desc=True).execute()
        invoices = []
        for row in (response.data or []):
            inv_id_val = str(row.get("invoice_id") or row.get("id") or "")
            invoices.append({
                "id": inv_id_val,
                "name": str(row.get("file_name", "") or ""),
                "data": str(row.get("html_data", "") or ""),
                "created_at": str(row.get("created_at", "") or "")
            })
        return jsonify(invoices)
    except Exception as e:
        err_msg = format_supabase_error(e)
        print(f"Error fetching invoices from Supabase: {err_msg}")
        return jsonify({"error": f"Failed to fetch invoices from Supabase: {err_msg}"}), 500


@app.route("/get-invoice/<invoice_id>")
def get_invoice(invoice_id):
    db = get_supabase()
    if not db:
        return jsonify({"error": "Supabase client is not configured"}), 500

    try:
        response = db.table("invoices").select("id, invoice_id, file_name, html_data, created_at").eq("invoice_id", str(invoice_id)).execute()
        if not (response.data and len(response.data) > 0):
            try:
                inv_id_int = int(invoice_id)
                response = db.table("invoices").select("id, invoice_id, file_name, html_data, created_at").eq("id", inv_id_int).execute()
            except (ValueError, TypeError):
                pass

        if response.data and len(response.data) > 0:
            row = response.data[0]
            return jsonify({
                "id": str(row.get("invoice_id") or row.get("id")),
                "name": str(row.get("file_name", "") or ""),
                "data": str(row.get("html_data", "") or "")
            })

        return jsonify({
            "id": str(invoice_id),
            "name": "",
            "data": ""
        })
    except Exception as e:
        err_msg = format_supabase_error(e)
        print(f"Error fetching invoice {invoice_id} from Supabase: {err_msg}")
        return jsonify({"error": f"Failed to fetch invoice: {err_msg}"}), 500


@app.route("/save", methods=["POST"])
def save():
    db = get_supabase()
    if not db:
        return jsonify({"error": "Supabase client is not configured"}), 500

    data = request.json or {}
    file_name = data.get("name", "").strip()
    html_data = data.get("data", "")
    custom_inv_id = str(data.get("invoice_id") or "").strip()

    if not file_name:
        return jsonify({"error": "Invoice name is required"}), 400

    invoice_id = custom_inv_id if custom_inv_id else str(int(time.time() * 1000))

    try:
        response = db.table("invoices").insert({
            "invoice_id": invoice_id,
            "file_name": file_name,
            "html_data": html_data
        }).execute()

        return jsonify({
            "message": "Invoice saved",
            "invoice_id": invoice_id
        })
    except Exception as e:
        err_msg = format_supabase_error(e)
        print(f"Error saving invoice to Supabase: {err_msg}")
        return jsonify({"error": f"Failed to save invoice to Supabase: {err_msg}"}), 500


@app.route("/update-invoice", methods=["POST"])
def update_invoice():
    db = get_supabase()
    if not db:
        return jsonify({"error": "Supabase client is not configured"}), 500

    data = request.json or {}
    inv_id = str(data.get("id", "")).strip()
    file_name = data.get("name", "").strip()
    html_data = data.get("data", "")

    try:
        update_payload = {"html_data": html_data}
        if file_name:
            update_payload["file_name"] = file_name

        db.table("invoices").update(update_payload).eq("invoice_id", inv_id).execute()

        return jsonify({
            "message": "Invoice updated"
        })
    except Exception as e:
        err_msg = format_supabase_error(e)
        print(f"Error updating invoice {inv_id} in Supabase: {err_msg}")
        return jsonify({"error": f"Failed to update invoice in Supabase: {err_msg}"}), 500


@app.route("/rename-invoice", methods=["POST"])
def rename_invoice():
    db = get_supabase()
    if not db:
        return jsonify({"error": "Supabase client is not configured"}), 500

    data = request.json or {}
    old_id = str(data.get("old_id", "")).strip()
    new_name = data.get("new_id", "").strip()

    try:
        db.table("invoices").update({
            "file_name": new_name
        }).eq("invoice_id", old_id).execute()

        return jsonify({
            "message": "Renamed"
        })
    except Exception as e:
        err_msg = format_supabase_error(e)
        print(f"Error renaming invoice {old_id} in Supabase: {err_msg}")
        return jsonify({"error": f"Failed to rename invoice in Supabase: {err_msg}"}), 500


@app.route("/delete-invoice", methods=["POST"])
def delete_invoice():
    db = get_supabase()
    if not db:
        return jsonify({"error": "Supabase client is not configured"}), 500

    data = request.json or {}
    delete_id = str(data.get("id", "")).strip()

    try:
        db.table("invoices").delete().eq("invoice_id", delete_id).execute()

        return jsonify({
            "message": "Deleted"
        })
    except Exception as e:
        err_msg = format_supabase_error(e)
        print(f"Error deleting invoice {delete_id} from Supabase: {err_msg}")
        return jsonify({"error": f"Failed to delete invoice from Supabase: {err_msg}"}), 500


@app.route("/pdf-action", methods=["POST"])
def pdf_action():
    if "file" in request.files:
        file = request.files["file"]
        pdf_bytes = file.read()

        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=False,
            download_name="invoice.pdf"
        )

    return jsonify({
        "error": "No file provided"
    }), 400


# ---------------------------------------------------------
# START APPLICATION
# ---------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")

    # Automatically open the billing website in Chrome for local development
    if host in ["127.0.0.1", "localhost"] and not os.environ.get("RENDER"):
        def open_browser():
            chrome_paths = [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ]
            opened = False
            for p in chrome_paths:
                if os.path.exists(p):
                    try:
                        webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(p))
                        webbrowser.get('chrome').open(f"http://127.0.0.1:{port}")
                        opened = True
                        break
                    except Exception:
                        pass
            if not opened:
                try:
                    webbrowser.open(f"http://127.0.0.1:{port}")
                except Exception:
                    pass

        threading.Timer(1.5, open_browser).start()

    app.run(
        host=host,
        port=port,
        debug=False,
        use_reloader=False
    )
