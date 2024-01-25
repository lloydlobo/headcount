import re
import uuid
import os

import requests
from flask import Flask, render_template, request
from markupsafe import Markup

# =============================================================================
# server/config
# =============================================================================


class Config:
    APP_RUN_DEBUG = True
    API_URL = os.getenv("API_URL", "https://jsonplaceholder.typicode.com/users")
    DEBUG_SLEEP = False
    DEBUG_SLEEP_SECS = 1


# =============================================================================
# server/models
# =============================================================================


class Contact:
    def __init__(self, id, name, email, phone, status="Inactive", **kwargs) -> None:
        self.id = id
        self.name = name
        self.email = email
        self.phone = phone
        self.status = status

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "status": self.status,
        }


def get_users(api_url):
    try:
        response = requests.get(api_url)
        response.raise_for_status()  # Raises HTTPError, if one occurred.
        return response.json()
    except requests.RequestException as err:
        print(f"Error fetching user data: {err}")
        return []


# =============================================================================
# INITIALIZE SERVER APP
# =============================================================================

app: Flask = Flask(__name__)
app.config.from_object(Config)

# =============================================================================
# INITIALIZE MODELS
# =============================================================================

contacts = [
    Contact(**user_data) for user_data in get_users(api_url=app.config["API_URL"])
]
contacts.sort(key=lambda contact: contact.name)
for contact in contacts:
    contact.status = "Active"
    contact.id = uuid.uuid4()


# =============================================================================
# server/views/rendering
# =============================================================================


def contact_as_li(contact):
    return Markup(render_template("partials/li_contact.html", contact=contact))


def contact_as_row_tr(contact, clazz=""):
    # NOTE: `value` is a string representing the value of the checkbox. This is not displayed on the client-side,
    # but on the server this is the value given to the data submitted with the checkboxes name.

    id_ = contact.id  # FIXME: this is visible!!!

    return Markup(
        render_template(
            "partials/tr_contact.html", contact=contact, clazz=clazz, id_=id_
        )
    )


def contacts_to_html_table():
    row_tr_contacts = Markup(
        f'{"".join([contact_as_row_tr(contact) for contact in contacts])}'
    )

    return Markup(
        render_template("partials/table_contacts.html", row_tr_contacts=row_tr_contacts)
    )


# =============================================================================
# server/views/pages
# =============================================================================


@app.route("/")
def index():
    return render_template("index.html")


# =============================================================================
# server/views/contacts
# =============================================================================


@app.route("/contacts")
def get_contacts():
    if app.config.get("DEBUG_SLEEP", False):
        import time

        time.sleep(app.config.get("DEBUG_SLEEP_SECS", 1))

    return contacts_to_html_table()


@app.route("/activate", methods=["PUT"])
def activate_contact():
    """If you want to stop polling from a server response you can respond with the HTTP response code 286 and the element will cancel the polling."""
    ids = request.form.getlist("ids")
    seen = set()

    for i, contact in enumerate(contacts):
        if (str(contact.id) in ids) and (contact.status == "Inactive"):
            seen.add(contact.id)
            contacts[i].status = "Active"

    rows = [
        contact_as_row_tr(
            contact=contact, clazz="activate" if contact.id in seen else ""
        )
        for contact in contacts
    ]

    return Markup(f'{"".join(rows)}')


@app.route("/deactivate", methods=["PUT"])
def deactivate_contact():
    """If you want to stop polling from a server response you can respond with the HTTP response code 286 and the element will cancel the polling."""
    ids = request.form.getlist("ids")
    seen = set()

    for i, contact in enumerate(contacts):
        if (str(contact.id) in ids) and (contact.status == "Active"):
            seen.add(contact.id)
            contacts[i].status = "Inactive"

    rows = [
        contact_as_row_tr(
            contact=contact, clazz="deactivate" if contact.id in seen else ""
        )
        for contact in contacts
    ]

    return Markup(f'{"".join(rows)}')


# =============================================================================
# server/views/forms
# =============================================================================


# FIXME: This does not stop from submitting invalid or existing emails.
@app.route("/contact/email", methods=["POST"])
def validate_inline_email():
    email: str | None = request.form.get("email")
    pattern = r"^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    matches = re.match(pattern, email)
    is_valid = bool(matches)

    exists = (
        any([contact.email == email for contact in contacts]) if is_valid else False
    )
    is_err = (not is_valid) or exists

    msg = "Invalid email" if not is_valid else "Email already exists" if exists else ""

    return Markup(
        render_template(
            "partials/validate_email_inline.html", email=email, is_err=is_err, msg=msg
        )
    )


@app.route("/search-contact", methods=["GET"])
def search_contact():
    keyword = request.args.get("q", default="", type=str).strip()

    if not keyword:
        return ""

    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    matches = [
        contact_as_li(contact=contact)
        for contact in contacts
        if pattern.search(contact.name)
    ]

    return Markup(f'<ul>{"".join(matches)}</ul>') if matches else "Not found"


@app.route("/form-add-contact", methods=["GET"])
def get_form_add_contact():
    return render_template("partials/form_add_contact.html")


@app.route("/add-contact", methods=["POST"])
def add_contact():
    new_contact = Contact(
        id=uuid.uuid4(),
        name=request.form.get("name"),
        email=request.form.get("email"),
        phone=request.form.get("phone"),
        status=request.form.get("status", "Inactive"),
    )

    contacts.append(new_contact)
    contacts.sort(key=lambda contact: contact.name)

    return contacts_to_html_table()


@app.route("/contact/<contact_id>", methods=["DELETE"])
def delete_contact(contact_id):
    """
    Each row has a button with a hx-delete attribute containing the url on which to issue a DELETE request to delete
    the row from the server. This request responds with a 200 status code and empty content, indicating that the row
    should be replaced with nothing.
    """
    index = None
    for i, contact in enumerate(contacts):
        if str(contact.id) == contact_id:
            index = i
            break

    if index is not None:
        contacts.pop(index)

    return ""


# =============================================================================
# server/views/statistics
# =============================================================================


@app.route("/count-contacts")
def count_contacts():
    return Markup(f"{len(contacts)} total")


@app.route("/count-active-contacts")
def count_active_contacts():
    active_count = sum(1 for contact in contacts if contact.status == "Active")
    return Markup(f"{active_count} active")


@app.route("/count-inactive-contacts")
def count_inactive_contacts():
    inactive_count = sum(1 for contact in contacts if contact.status == "Inactive")
    return Markup(f"{inactive_count} inactive")


# =============================================================================
# MAIN (DEVELOPMENT)
# =============================================================================


def main():
    app.run(debug=app.config.get("APP_RUN_DEBUG", True))


if __name__ == "__main__":
    main()
