import re
import uuid

import requests
from flask import Flask, render_template, request
from markupsafe import Markup

app = Flask(__name__)

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
    return Markup(f"""
        <tr class="{clazz}">
            <td>
                <label for="ids">
                    <input type='checkbox' name='ids' value='{id_}'>
                </label>
            </td>
            <td>{contact['name']}</td>
            <td>{contact['phone']}</td>
            <td>{contact['email']}</td>
            <td>{'Active' if (contact["status"] == 'Active') else 'Inactive'}</td>
            <td><button hx-delete="/contact/{id_}">DELETE</button></td>
        </tr>
    """)


def contacts_to_html_table():
    row_contacts = "".join([contact_as_row(contact) for contact in contacts])
    return Markup(f"""
        <h2 style="--pico-font-size: 1rem; --pico-color: var(--pico-secondary);">{len(contacts)} results</h2>
        <figure>
            <table >
                <thead>
                    <tr>
                        <th></th>
                        <th>Name</th>
                        <th>Phone</th>
                        <th>Email</th>
                        <th>Status</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody id="tbody">
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
    index = None
    for i, contact in enumerate(contacts):
        if str(contact["id"]) == contact_id:
            index = i
            break

    if index is not None:
        contacts.pop(index)

    # return contacts_to_html_table()


def main():
    app.run(debug=True)


if __name__ == "__main__":
    main()
