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

def get_user_role(user):
    """
    Determines the user's highest-level role based on their groups.
    Checks for 'admin' first, then 'user'.
    """
    admin_users = ROLE_CONFIG.get('roles', {}).get('admin', [])
    normal_users = ROLE_CONFIG.get('roles', {}).get('user', [])
    
    # Check for admin role
    if user in admin_users:
        return "admin"
    elif user in normal_users:
        return "user"
            
    return 'none' # No permissions

def get_current_user_context():
    """
    Simulates OpenShift's OAuth proxy by reading headers.
    """
    print(f"Headers: {request.headers}")

    # Load config in case it has changed
    load_config()

    # X-Forwarded-User is set by the OpenShift OAuth proxy
    user = request.headers.get('X-Forwarded-User', 'guest')
    print(f"Current user: {user}")
    
    # # X-Forwarded-Group is a comma-separated list of groups
    # groups_header = request.headers.get('X-Forwarded-Group', '')
    # print(f"Groups header: {groups_header}")
    # groups = [g.strip() for g in groups_header.split(',') if g.strip()]
    # print(f"Current group(s): {groups}")
    groups = []
   
    # role = get_user_role(groups)
    role = get_user_role(user)
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
<head>
  <title>Dashboard</title>
  <style>
    body { 
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; 
      background-color: #f4f7fa;
      margin: 20px;
    }
    h1, h3 { color: #333; }
    hr { border: 0; border-top: 1px solid #eee; }
    a { color: #007bff; text-decoration: none; }

    /* --- NEW HEADER & LOGOUT --- */
    .header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 2px solid #eee;
      padding-bottom: 10px;
    }
    .header h1 {
      margin: 0;
      border: 0;
      padding: 0;
      font-size: 28px;
    }
    .logout-button {
      background-color: #dc3545;
      color: white;
      padding: 8px 15px;
      border-radius: 5px;
      font-weight: 500;
      text-decoration: none;
      transition: background-color 0.2s ease-in-out;
    }
    .logout-button:hover {
      background-color: #c82333;
      color: white;
    }
    /* --- END NEW --- */
    
    /* Widget Layout */
    .widget-container {
      display: flex;
      flex-wrap: wrap;
      gap: 20px;
      margin-top: 25px;
      margin-bottom: 25px;
    }
    .widget-card {
      background-color: #ffffff;
      border-radius: 8px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      padding: 20px;
      flex-basis: 300px; /* Each widget has a base width */
      flex-grow: 1;
      text-align: center;
    }
    .widget-card h4 {
      margin-top: 0;
      color: #555;
    }

    /* Dial Widget (Conic Gradient) */
    .dial {
      width: 150px;
      height: 150px;
      border-radius: 50%;
      background: conic-gradient(#28a745 0% 65%, #e9ecef 65% 100%);
      position: relative;
      margin: 10px auto; /* Center it */
    }
    .dial-center {
      position: absolute;
      width: 70%;
      height: 70%;
      top: 15%;
      left: 15%;
      background: #ffffff;
      border-radius: 50%;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      font-size: 28px;
      font-weight: bold;
      color: #28a745;
    }
    .dial-center span {
      font-size: 14px;
      color: #6c757d;
      font-weight: normal;
    }

    /* Bar Widget */
    .bar-label {
      text-align: left; 
      margin: 10px 0 5px 0; 
      font-size: 14px;
      font-weight: 500;
    }
    .bar-container {
      width: 100%;
      background-color: #e9ecef;
      border-radius: 20px;
      height: 25px;
      overflow: hidden;
      box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
    }
    .bar-fill {
      width: 45%; /* Mock value */
      height: 100%;
      background-color: #007bff;
      border-radius: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      font-size: 12px;
      font-weight: bold;
      transition: width 0.5s ease-in-out;
    }
    .bar-fill.warning {
      width: 82%;
      background-color: #ffc107;
      color: #333;
    }
  </style>
</head>
<body>
  
  <div class="header">
    <h1>Welcome, {{ user }}!</h1>
    <a href="/oauth/sign_out" class="logout-button">Logout</a>
  </div>
  <p style="margin-top: 15px;">Your role is: <strong>{{ role }}</strong></p>
  
  {% if role == 'admin' %}
    <p><strong><a href="/admin">Go to Admin Panel</a></strong></p>
  {% endif %}
  <hr>
  
  <h3>Dashboard Widgets</h3>

  <div class="widget-container">
    
    <div class="widget-card">
      <h4>System Health</h4>
      <div class="dial">
        <div class="dial-center">
          65%
          <span>Uptime</span>
        </div>
      </div>
      <p style="font-size: 14px; color: #666;">All systems operational.</p>
    </div>
    
    <div class="widget-card">
      <h4>Resource Utilization</h4>
      
      <p class="bar-label">CPU Load</p>
      <div class="bar-container">
        <div class="bar-fill">45%</div>
      </div>
      
      <p class="bar-label" style="margin-top: 20px;">Memory Usage</p>
      <div class="bar-container">
        <div class="bar-fill warning">82%</div>
      </div>
    </div>
    
  </div>

  <h3>Logs</h3>
  <p>Here is your basic user-level dashboard information and logs.</p>

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
