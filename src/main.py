import os
import yaml
from flask import Flask, request, render_template_string, abort

app = Flask(__name__)

# The path where OpenShift will mount the ConfigMap
CONFIG_FILE_PATH = os.environ.get('CONFIG_FILE_PATH', '/config/roles.yaml')
ROLE_CONFIG = {}

def load_config():
    """Loads the role mapping from the mounted ConfigMap file."""
    global ROLE_CONFIG
    try:
        with open(CONFIG_FILE_PATH, 'r') as f:
            ROLE_CONFIG = yaml.safe_load(f)
            print(f"Successfully loaded config from {CONFIG_FILE_PATH}")
    except FileNotFoundError:
        print(f"Error: Config file not found at {CONFIG_FILE_PATH}.")
        print("Running with empty config. All role checks will fail.")
        ROLE_CONFIG = {'roles': {}}
    except Exception as e:
        print(f"Error loading config: {e}")
        ROLE_CONFIG = {'roles': {}}

def get_user_role(groups):
    """
    Determines the user's highest-level role based on their groups.
    Checks for 'admin' first, then 'user'.
    """
    admin_groups = ROLE_CONFIG.get('roles', {}).get('admin', [])
    user_groups = ROLE_CONFIG.get('roles', {}).get('user', [])
    
    # Check for admin role
    for group in groups:
        if group in admin_groups:
            return 'admin'
            
    # Check for user role
    for group in groups:
        if group in user_groups:
            return 'user'
            
    return 'none' # No permissions

def get_current_user_context():
    """
    Simulates OpenShift's OAuth proxy by reading headers.
    """
    print(f"Headers: {request.headers}")

    # X-Forwarded-User is set by the OpenShift OAuth proxy
    user = request.headers.get('X-Forwarded-User', 'guest')
    print(f"Current user: {user}")
    
    # X-Forwarded-Group is a comma-separated list of groups
    groups_header = request.headers.get('X-Forwarded-Group', '')
    print(f"Groups header: {groups_header}")
    groups = [g.strip() for g in groups_header.split(',') if g.strip()]
    print(f"Current group(s): {groups}")
   
    role = get_user_role(groups)
    print(f"Current role: {role}")
    return user, groups, role

# --- Templates (in-lined for simplicity) ---
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <title>Login Required</title>
  <style>
    body { 
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; 
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100vh;
      background-color: #f4f7fa;
      margin: 0;
    }
    .login-card {
      background-color: #ffffff;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      padding: 40px;
      text-align: center;
    }
    .login-button {
      display: inline-block;
      padding: 12px 24px;
      font-size: 16px;
      font-weight: 600;
      color: #ffffff;
      background-color: #007bff;
      border: 0;
      border-radius: 5px;
      text-decoration: none;
      margin-top: 20px;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <div class="login-card">
    <h2>Authentication Required</h2>
    <p>You must log in via OpenShift to access this dashboard.</p>
    <a href="/oauth/start?rd=/" class="login-button">Login with OpenShift</a>
  </div>
</body>
</html>
"""

ERROR_403_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><title>Access Denied</title></head>
<body>
  <h1>Access Denied (403 Forbidden)</h1>
  <p>Sorry, <strong>{{ user }}</strong>, you do not have permission to view this page.</p>
  <p>
    Your role ('<strong>{{ role }}</strong>', from groups: {{ groups }}) 
    is not authorized for this resource.
  </p>
  <p><a href="/">Back to Dashboard</a></p>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><title>Dashboard</title></head>
<body>
  <h1>Welcome to the Main Dashboard, {{ user }}!</h1>
  <p>Your role is: <strong>{{ role }}</strong></p>
  <p>Your groups are: {{ groups }}</p>
  <hr>
  <h3>Dashboard Content</h3>
  <p>Here is your basic user-level dashboard information.</p>
  
  {% if role == 'admin' %}
    <p><strong><a href="/admin">Go to Admin Panel</a></strong></p>
  {% endif %}
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><title>Admin Panel</title></head>
<body>
  <h1>Admin Control Panel</h1>
  <p>Welcome, <strong>{{ user }}</strong>. You have admin access.</p>
  <p>Your groups are: {{ groups }}</p>
  <hr>
  <h3>Admin Functions</h3>
  <ul>
    <li>Manage Users</li>
    <li>System Settings</li>
    <li>View Audit Logs</li>
  </ul>
  <p><a href="/">Back to Dashboard</a></p>
</body>
</html>
"""

ERROR_403_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head><title>Access Denied</title></head>
<body>
  <h1>Access Denied (403)</h1>
  <p>Sorry, <strong>{{ user }}</strong>, you do not have permission to view this page.</p>
  <p>Your role '<strong>{{ role }}</strong>' (from groups: {{ groups }}) is not authorized.</p>
</body>
</html>
"""

# --- Routes ---

@app.route('/')
def dashboard():
    """The main dashboard view. Accessible to 'user' and 'admin'."""
    user, groups, role = get_current_user_context()
    
    if role in ['admin', 'user']:
        return render_template_string(DASHBOARD_TEMPLATE, user=user, groups=groups, role=role)
    
    # If role is 'none', they are not authenticated. Show the login page.
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/admin')
def admin_panel():
    """The admin-only section."""
    user, groups, role = get_current_user_context()
    
    if role == 'admin':
        return render_template_string(ADMIN_TEMPLATE, user=user, groups=groups, role=role)
    
    elif role == 'user':
        # The user is logged in, but not an admin. This is a 403 Forbidden.
        return render_template_string(ERROR_403_TEMPLATE, user=user, groups=groups, role=role), 403
    
    else:
        # The user is not logged in at all (role == 'none'). Show the login page.
        return render_template_string(LOGIN_TEMPLATE)

if __name__ == '__main__':
    load_config() # Load config on startup
    app.run(host='0.0.0.0', port=8080)

def main():
    print("Hello from src!")
