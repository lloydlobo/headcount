import re
import uuid

import requests
from flask import Flask, render_template, request
from markupsafe import Markup

__DEBUG = False

# Flask app
app: Flask = Flask(__name__)

contacts = []


def get_users():
    response = requests.get("https://jsonplaceholder.typicode.com/users")
    if response.status_code == 200:
        return response.json()
    else:
        return ({"error": "Failed to fetch data from JSONPlaceholder"}), 500


contacts.extend(get_users())
contacts.sort(key=lambda x: x["name"])

# Initialize contact status and id.
for contact in contacts:
    contact["status"] = "Active"
    contact["id"] = str(contact["id"])
    contact["id"] = uuid.uuid4()


def contact_as_li(contact):
    return Markup(
        f""" 
        <li class="grid">
            <span>{contact["name"]}</span>
            <div class="grid">
                <span>{contact["phone"]}</span>
                <span>{contact["email"]}</span>
            </div>
        </li>
        """
    )


def contact_as_row(contact, clazz=""):
    # NOTE: `value` is a string representing the value of the checkbox. This is not displayed on the client-side,
    # but on the server this is the value given to the data submitted with the checkboxes name.
    id_ = contact["id"]  # FIXME: this is visible!!!
    delete_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>"""
    return Markup(
        f"""
        <tr class="{clazz}">
            <td scope="row">
                <label for="ids">
                    <input type='checkbox' name='ids' value='{id_}'>
                </label>
            </td>
            <td>{contact['name']}</td>
            <td>{contact['phone']}</td>
            <td>{contact['email']}</td>
            <td>{'Active' if (contact["status"] == 'Active') else 'Inactive'}</td>
            <td>
                <button 
                    hx-delete="/contact/{id_}" 
                    class="contrast"
                    data-tooltip="Remove {contact['name']}?"
                    data-placement="left"
                >
                    {delete_svg}
                </button>
            </td>
        </tr>
        """
    )


def contacts_to_html_table():
    row_contacts = "".join([contact_as_row(contact) for contact in contacts])
    # <h2 style="--pico-font-size: 1rem; --pico-color: var(--pico-secondary);">{len(contacts)} results</h2>
    return Markup(
        f"""
        <figure>
            <table class="!striped">
                <thead>
                    <tr>
                        <th scope="col"></th>
                        <th scope="col">Name</th>
                        <th scope="col">Phone</th>
                        <th scope="col">Email</th>
                        <th scope="col">Status</th>
                        <th scope="col"></th>
                    </tr>
                </thead>
                <tbody 
                    id="tbody"
                    hx-confirm="Are you sure?"
                    hx-target="closest tr"
                    hx-swap="outerHTML swap:1s"
                >
                    {row_contacts}
                </tbody>
            </table>
        </figure>
        """
    )


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/contacts")
def get_contacts():
    if __DEBUG:
        import time

        time.sleep(1)

    return contacts_to_html_table()


@app.route("/activate", methods=["PUT"])
def activate():
    """If you want to stop polling from a server response you can respond with the HTTP response code 286 and the element will cancel the polling."""
    ids = request.form.getlist("ids")
    seen = set()

    for i, c in enumerate(contacts):
        if str(c["id"]) in ids:
            seen.add(c["id"])
            contacts[i]["status"] = "Active"

    rows = [
        contact_as_row(
            contact=contact, clazz="activate" if contact["id"] in seen else ""
        )
        for contact in contacts
    ]
    html = "".join(rows)
    return Markup(f"{html}")


@app.route("/deactivate", methods=["PUT"])
def deactivate():
    """If you want to stop polling from a server response you can respond with the HTTP response code 286 and the element will cancel the polling."""
    ids = request.form.getlist("ids")
    seen = set()

    for i, c in enumerate(contacts):
        if str(c["id"]) in ids:
            seen.add(c["id"])
            contacts[i]["status"] = "Inactive"

    rows = [
        contact_as_row(
            contact=contact, clazz="deactivate" if contact["id"] in seen else ""
        )
        for contact in contacts
    ]
    html = "".join(rows)
    return Markup(f"{html}")


@app.route("/contact/email", methods=["POST"])
def validate_email_with_partial():
    email: str | None = request.form.get("email")
    pattern = r"^\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

    matches = re.match(pattern, email)
    is_valid = bool(matches)

    exists = any([con["email"] == email for con in contacts]) if is_valid else False
    is_err = (not is_valid) or exists

    msg = "Invalid email" if not is_valid else "Email already exists" if exists else ""

    return Markup(
        f"""
        <div hx-target="this" hx-swap="outerHTML">
            <label for="email">Email </label>
            <input
                name="email"
                hx-post="/contact/email"
                hx-indicator="#ind"
                value={"&nbsp;" if email.isspace() else email}
                aria-describedby="email-helper"
                aria-invalid={"true" if is_err else "false"}
                aria-label="email"
                autocomplete="email"
                id="email"
                placeholder="Email"
                required
                type="email"
            />
            <small id="email-helper">{msg}</small>
        </div>
        """
    )


@app.route("/search_contact", methods=["GET"])
def search_contact():
    keyword = request.args.get("q", default="", type=str).strip()

    if not keyword:
        return ""

    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
    matches = [contact_as_li(contact=m) for m in contacts if pattern.search(m["name"])]

    return Markup(f'<ul>{"".join(matches)}</ul>') if matches else "Not found"


@app.route("/add_contact", methods=["POST"])
def add_contact():
    new_contact = {
        "id": uuid.uuid4(),
        "name": request.form.get("name"),
        "email": request.form.get("email"),
        "phone": request.form.get("phone"),
        "status": request.form.get("status", "Inactive"),
    }

    contacts.append(new_contact)
    contacts.sort(key=lambda x: x["name"])

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
        if str(contact["id"]) == contact_id:
            index = i
            break

    if index is not None:
        contacts.pop(index)

    return ""


@app.route("/count-contacts")
def count_contacts():
    return Markup(f"{len(contacts)} total")


@app.route("/count-active-contacts")
def count_active_contacts():
    counter = 0
    for c in contacts:
        if c["status"] == "Active":
            counter += 1
    return Markup(f"{counter} active")


@app.route("/count-inactive-contacts")
def count_inactive_contacts():
    counter = 0
    for c in contacts:
        if c["status"] == "Inactive":
            counter += 1
    return Markup(f"{counter} inactive")


@app.route("/modal", methods=["GET"])
def get_modal():
    return Markup(
        f"""
        <div
          id="modal"
          _="on closeModal add .closing then wait for animationend then remove me"
        >
          <div class="modal-underlay" _="on click trigger closeModal"></div>
          <div class="modal-content">
            <form
              data-post="/add_contact"
              hx-post="/add_contact"
              hx-target="#contact-list"
            >
              <article>
                <header><b>Add new headcount</b></header>
                <label for="name" class="sr-only">Name </label>
                <input type="text" id="name" name="name" placeholder="Name" required />
                <label for="phone" class="sr-only">Phone</label>
                <input type="tel" id="phone" name="phone" placeholder="Phone" required />
                <div hx-target="this" hx-swap="outerHTML">
                  <label for="email" class="sr-only">Email</label>
                  <input
                    name="email"
                    hx-post="/contact/email"
                    hx-indicator="#ind"
                    aria-label="email"
                    aria-describedby="email-helper"
                    autocomplete="email"
                    id="email"
                    placeholder="Email"
                    required
                    type="email"
                  />
                  <img
                    src="static/assets/img/loader.gif"
                    id="ind"
                    alt="Loading..."
                    class="htmx-indicator"
                    aria-busy="true"
                  />
                </div>
                <fieldset>
                  <legend>Status</legend>
                  <input type="checkbox" id="status" name="status" />
                  <label for="status">Active</label>
                </fieldset>
                <div class="grid">
                  <div></div>
                  <div></div>
                  <button
                    class="secondary"
                    type="button"
                    _="on click trigger closeModal"
                    data-tooltip="Close form"
                  >
                    Close
                  </button>
                  <button type="submit" data-tooltip="Add new">Submit</button>
                </div>
              </article>
            </form>
          </div>
        </div>
        """
    )


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
