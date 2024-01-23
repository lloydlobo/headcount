import re
import uuid

import requests
from flask import Flask, render_template, request
from markupsafe import Markup

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
    return Markup(f""" 
        <li class="grid">
            <span>{contact["name"]}</span>
            <div class="grid">
                <span>{contact["phone"]}</span>
                <span>{contact["email"]}</span>
            </div>
        </li>
    """)


def contact_as_row(contact, clazz=""):
    # NOTE: `value` is a string representing the value of the checkbox. This is not displayed on the client-side,
    # but on the server this is the value given to the data submitted with the checkboxes name.
    id_ = contact["id"]  # FIXME: this is visible!!!
    delete_svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-trash"><path d="M3 6h18"/><path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"/><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2"/></svg>"""
    return Markup(f"""
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
    """)


def contacts_to_html_table():
    row_contacts = "".join([contact_as_row(contact) for contact in contacts])
    # <h2 style="--pico-font-size: 1rem; --pico-color: var(--pico-secondary);">{len(contacts)} results</h2>
    return Markup(f"""
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
    """)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/contacts")
def get_contacts():
    # import time
    # time.sleep(1)
    return contacts_to_html_table()


@app.route("/activate", methods=["PUT"])
def activate():
    ids = request.form.getlist("ids")
    seen = set()

    for i, c in enumerate(contacts):
        if str(c["id"]) in ids:
            seen.add(c["id"])
            contacts[i]["status"] = "Active"

    rows = [contact_as_row(contact=contact, clazz="activate" if contact["id"] in seen else "")
            for contact in contacts]
    html = ''.join(rows)
    return Markup(f"{html}")


@app.route("/deactivate", methods=["PUT"])
def deactivate():
    ids = request.form.getlist("ids")
    seen = set()

    for i, c in enumerate(contacts):
        if str(c["id"]) in ids:
            seen.add(c["id"])
            contacts[i]["status"] = "Inactive"

    rows = [contact_as_row(contact=contact, clazz="deactivate" if contact["id"] in seen else "")
            for contact in contacts]
    html = ''.join(rows)
    return Markup(f"{html}")


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
        "id"    : uuid.uuid4(),
        "name"  : request.form.get("name"),
        "email" : request.form.get("email"),
        "phone" : request.form.get("phone"),
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
    return Markup(f"""
        <div id="modal" _="on closeModal add .closing then wait for animationend then remove me">
            <div class="modal-underlay" _="on click trigger closeModal"></div>
            <div class="modal-content">
                <h1>Modal Dialog</h1>
                This is the modal content.
                You can put anything here, like text, or a form, or an image.
                <br>
                <br>
                <button _="on click trigger closeModal">Close</button>
            </div>
        </div>
    """)

# def main():
#     app.run(debug=True)
#
#
# if __name__ == "__main__":
#     main()
