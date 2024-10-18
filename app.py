from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import urllib.parse
import json
import os
import hashlib

USER_FILE = "users.json"
TASK_FILE = "tasks.json"
SESSION_COOKIE_NAME = "session_id"
sessions = {}
users = {}
tasks = {}

# Load users from file
def load_users():
    global users
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            try:
                data = f.read().strip()
                if data:  # Check if the file is not empty
                    users = json.loads(data)
                else:
                    users = {}  # Initialize to empty dict if the file is empty
            except json.JSONDecodeError:
                print(f"Error: Failed to parse {USER_FILE}. Initializing empty users.")
                users = {}  # Initialize to empty dict if JSON is invalid
    else:
        users = {}  # Initialize to empty dict if the file doesn't exist
# Save users to file
def save_users():
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

# Load tasks from file
def load_tasks():
    global tasks
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE, "r") as f:
            try:
                data = f.read().strip()
                if data:
                    # Ensure tasks is loaded as a dictionary
                    tasks = json.loads(data)
                    if not isinstance(tasks, dict):
                        print(f"Warning: Expected tasks to be a dictionary, but got {type(tasks)}. Initializing to empty dict.")
                        tasks = {}  # Initialize to empty dict if not a dictionary
                else:
                    tasks = {}  # Initialize to empty dict if the file is empty
            except json.JSONDecodeError:
                print(f"Error: Failed to parse {TASK_FILE}. Initializing empty tasks.")
                tasks = {}  # Initialize to empty dict if JSON is invalid

# Save tasks to file
def save_tasks():
    with open(TASK_FILE, "w") as f:
        json.dump(tasks, f)

# Password hashing function
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Session handling
def get_session_user(headers):
    cookies = headers.get('Cookie')
    if cookies:
        cookies = cookies.split('; ')
        for cookie in cookies:
            key, value = cookie.split('=')
            if key == SESSION_COOKIE_NAME and value in sessions:
                return sessions[value]
    return None

# Load users and tasks initially
load_users()
load_tasks()

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        query_params = urllib.parse.parse_qs(parsed_path.query)
        user = get_session_user(self.headers)
        if parsed_path.path == "/css/style.css":
            self.send_response(200)
            self.send_header("Content-type", "text/css")
            self.end_headers()
            with open("css/style.css", "rb") as f:  # Open the CSS file in binary mode
                self.wfile.write(f.read())
            return
        
        elif parsed_path.path.startswith("/img/"):
            img_path = parsed_path.path.lstrip('/')  # Remove leading slash
            try:
                # Determine the content type based on file extension
                if img_path.endswith(".svg"):
                    content_type = "image/svg+xml"
                elif img_path.endswith((".jpg", ".jpeg")):
                    content_type = "image/jpeg"
                elif img_path.endswith(".png"):
                    content_type = "image/png"
                else:
                    content_type = "application/octet-stream"  # Fallback for unknown types

                self.send_response(200)
                self.send_header("Content-type", content_type)
                self.end_headers()
                with open(img_path, "rb") as f:  # Open the image file in binary mode
                    self.wfile.write(f.read())
                return
            except FileNotFoundError:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Image not found")
                return

        if parsed_path.path == "/login":
            self.serve_html("login.html")
        elif parsed_path.path == "/register":
            self.serve_html("registration.html")
        elif parsed_path.path == "/tasks" and user:
            # Serve the tasks page if the user is logged in
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()

            # Load tasks for the current user
            user_tasks = tasks.get(user, [])
            total_tasks = len(user_tasks)
            completed_tasks = sum(1 for task in user_tasks if task.get("status") == "Completed")

            # Generate task list with Edit, Delete, and Status Selector
            task_list = "".join([f"""
                <li class="task-item">
                    <div class="task-date">
                        
            """ + (
                f"""
                        <div class="date-block">
                            <p class="day">{datetime.strptime(task.get('due_date', ''), '%Y-%m-%d').day}</p>
                            <p class="month_name">{datetime.strptime(task.get('due_date', ''), '%Y-%m-%d').strftime('%b')}</p>
                        </div>
                            <p class="year">{datetime.strptime(task.get('due_date', ''), '%Y-%m-%d').year}</p>
                """ if task.get('due_date') else """
                            <p class="day">No due date</p>
                            <p class="month_name"></p>
                            <p class="year"></p>
                """
            ) + f"""
                    </div>
                    <p class="task" style="{'text-decoration: line-through; color: #32be8f; foxr-weight: 500;' if task.get('status') == 'Completed' else ''}">
                        {task['text']}
                    </p>
                    <div class="buttons">
                        <form method="GET" action="/edit-task">
                            <input type="hidden" name="task_id" value="{idx}">
                            <button type="submit" class="edit">Edit</button>
                        </form>
                        <form method="POST" action="/delete-task">
                            <input type="hidden" name="task_id" value="{idx}">
                            <button type="submit" class="delete">Delete</button>
                        </form>
                        <form method="POST" action="/update-status">
                            <input type="hidden" name="task_id" value="{idx}">
                            <select name="status" onchange="this.form.submit()">
                                <option value="Not Started" {'selected' if task.get('status') == 'Not Started' else ''}>Not Started</option>
                                <option value="In Progress" {'selected' if task.get('status') == 'In Progress' else ''}>In Progress</option>
                                <option value="Completed" {'selected' if task.get('status') == 'Completed' else ''}>Completed</option>
                            </select>
                        </form>
                    </div>
                </li>
            """ for idx, task in enumerate(user_tasks)])

            # After generating the task list, read the HTML template and inject the task list
            with open("tasks.html", "r") as f:
                html = f.read().replace("{TASK_LIST}", task_list)
                # Add total tasks and completed tasks to the HTML
                html = html.replace("{TOTAL_TASKS}", str(total_tasks))
                html = html.replace("{COMPLETED_TASKS}", str(completed_tasks))

                self.wfile.write(html.encode())



        elif parsed_path.path == "/edit-task" and user and "task_id" in query_params:
            task_id = int(query_params["task_id"][0])
            user_tasks = tasks.get(user, [])

            if task_id < len(user_tasks):
                task = user_tasks[task_id]
                task_status = task.get("status", "Not Started")  # Get the task's status or default to "Not Started"

                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()

                with open("edit-task.html", "r") as f:
                    html = f.read()

                # Replace task_id, task text, and task status in the template
                html = html.replace("{{ task_id }}", str(task_id))
                html = html.replace("{{ task }}", task["text"])
                html = html.replace("{{ task_status }}", task_status)

                self.wfile.write(html.encode())

            else:
                self.send_response(404)
                self.end_headers()

        else:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = urllib.parse.parse_qs(post_data.decode())
        user = get_session_user(self.headers)

        if parsed_path.path == "/register":
            username = data.get("username")[0]
            password = hash_password(data.get("password")[0])

            print("Current users:", users)  # Debug line
            if username in users:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"User already exists")
            else:
                users[username] = {"password": password}
                tasks[username] = []  # Initialize an empty task list for the new user
                save_users()  # Save updated users
                save_tasks()  # Save tasks if needed
                self.send_response(303)
                self.send_header("Location", "/login")
                self.end_headers()

        elif parsed_path.path == "/login":
            username = data.get("username")[0]
            password = hash_password(data.get("password")[0])

            if username in users and users[username]["password"] == password:
                session_id = str(len(sessions) + 1)
                sessions[session_id] = username
                self.send_response(303)
                self.send_header("Set-Cookie", f"{SESSION_COOKIE_NAME}={session_id}")
                self.send_header("Location", "/tasks")
                self.end_headers()
            else:
                self.send_response(403)
                self.end_headers()
                self.wfile.write(b"Invalid credentials")

        elif user:
            if parsed_path.path == "/":
                # Get task text and status
               task_text = data.get("task")[0]
               due_date = data.get("due_date")[0]
               tasks[user].append({"text": task_text, "status": "Not started", "due_date": due_date,})
               save_tasks()
               self.send_response(303)
               self.send_header("Location", "/tasks")
               self.end_headers()

            elif parsed_path.path == "/delete-task":
                task_id = int(data.get("task_id")[0])
                tasks[user].pop(task_id)
                save_tasks()
                self.send_response(303)
                self.send_header("Location", "/tasks")
                self.end_headers()

            elif parsed_path.path == "/update-status" and user:
                # Get the task ID and new status from the form data
                task_id = int(data.get("task_id")[0])
                new_status = data.get("status")[0]
                
                # Load the tasks for the current user
                user_tasks = tasks.get(user, [])
                
                if task_id < len(user_tasks):
                    # Update the task's status
                    user_tasks[task_id]["status"] = new_status
                    
                    # Recalculate completed tasks
                    total_tasks = len(user_tasks)
                    completed_tasks = sum(1 for task in user_tasks if task.get("status") == "Completed")
                    
                    # Save updated tasks
                    save_tasks()
                    
                    # Send response and redirect back to the tasks page
                    self.send_response(303)
                    self.send_header("Location", "/tasks")
                    self.end_headers()
                else:
                    # Handle case where the task ID is invalid
                    self.send_response(404)
                    self.end_headers()


            elif parsed_path.path == "/edit-task":
                task_id = int(data.get("task_id")[0])
                updated_task_text = data.get("updated_task")  # No indexing here

                if updated_task_text and len(updated_task_text) > 0:
                    tasks[user][task_id]['text'] = updated_task_text[0]  # Only access if it's not None
                    save_tasks()
                    self.send_response(303)
                    self.send_header("Location", "/tasks")
                    self.end_headers()
                else:
                    # Handle case where updated_task_text is None or empty
                    self.send_response(400)  # Bad Request
                    self.end_headers()
                    self.wfile.write(b"Bad Request: Task text is required.")

                    save_tasks()
                    self.send_response(303)
                    self.send_header("Location", "/tasks")
                    self.end_headers()

        else:
            self.send_response(302)
            self.send_header("Location", "/login")
            self.end_headers()

    def serve_html(self, filename):
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        with open(filename, "r") as f:
            html = f.read()
        self.wfile.write(html.encode())

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8080):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting server on port {port}")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
