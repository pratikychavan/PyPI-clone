#!/usr/bin/env python3
"""
Enhanced PyPI Clone Server with improved features

This is an enhanced version of the PyPI clone with:
- Better package management
- Authentication system
- API tokens
- Admin interface
- Package statistics
- Better error handling
"""

import os
import sys
from pathlib import Path
from flask import Flask, request, jsonify, render_template_string, send_file, abort, redirect, url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

# Import our modules
from config import Config
from package_manager import PackageManager
from auth import UserManager, SimpleAuth

app = Flask(__name__)

# Load configuration
config = Config()
app.config['SECRET_KEY'] = config.secret_key
app.config['MAX_CONTENT_LENGTH'] = config.max_file_size

# Initialize managers
package_manager = PackageManager(config.data_dir)
user_manager = UserManager()
auth = SimpleAuth(user_manager)

@app.errorhandler(413)
def too_large(e):
    return jsonify({'error': 'File too large'}), 413

@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return jsonify({'error': f'File too large. Maximum size is {config.max_file_size} bytes'}), 413

@app.route('/')
def index():
    """Main web interface"""
    packages = package_manager.get_all_packages()
    stats = package_manager.get_package_stats()
    return render_template_string(ENHANCED_INDEX_TEMPLATE, 
                                packages=packages, 
                                stats=stats, 
                                auth_enabled=config.auth_enabled)

@app.route('/simple/')
def simple_index():
    """PyPI simple API - package index"""
    packages = package_manager.get_all_packages()
    package_names = sorted(packages.keys())
    
    html = """<!DOCTYPE html>
<html>
<head>
    <title>Simple index</title>
</head>
<body>
    <h1>Simple index</h1>
"""
    
    for name in package_names:
        html += f'    <a href="/simple/{name}/">{name}</a><br>\n'
    
    html += """</body>
</html>"""
    
    return html

@app.route('/simple/<package_name>/')
def simple_package(package_name):
    """PyPI simple API - package versions"""
    packages = package_manager.get_all_packages()
    package_name_lower = package_name.lower()
    
    if package_name_lower not in packages:
        abort(404)
    
    package_files = packages[package_name_lower]
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Links for {package_name}</title>
</head>
<body>
    <h1>Links for {package_name}</h1>
"""
    
    for file_info in package_files:
        filename = file_info['filename']
        md5_hash = file_info.get('md5_digest', '')
        sha256_hash = file_info.get('sha256_digest', '')
        html += f'    <a href="/packages/{filename}#sha256={sha256_hash}" data-dist-info-metadata="sha256={sha256_hash}">{filename}</a><br>\n'
    
    html += """</body>
</html>"""
    
    return html

@app.route('/packages/<filename>')
def download_package(filename):
    """Download package file"""
    filename = secure_filename(filename)
    file_path = Path(config.data_dir) / filename
    
    # Also check in subdirectories
    if not file_path.exists():
        found = False
        for file_path in Path(config.data_dir).rglob(filename):
            if file_path.is_file():
                found = True
                break
        if not found:
            abort(404)
    
    return send_file(str(file_path), as_attachment=True)

@app.route('/upload', methods=['POST'])
@auth.require_auth() if config.auth_enabled else lambda f: f
def upload_package():
    """Upload package file"""
    # Check if file was uploaded
    if 'content' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['content']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type
    if not (file.filename.endswith('.whl') or file.filename.endswith('.tar.gz')):
        return jsonify({'error': 'Only .whl and .tar.gz files are supported'}), 400
    
    # Read file data
    file_data = file.read()
    if len(file_data) == 0:
        return jsonify({'error': 'Empty file'}), 400
    
    filename = secure_filename(file.filename)
    
    try:
        # Check if file already exists
        file_path = Path(config.data_dir) / filename
        if file_path.exists():
            return jsonify({'error': 'File already exists'}), 409
        
        # Store the package
        stored_path = package_manager.store_package(file_data, filename)
        
        # Get package info for response
        package_info = package_manager.get_package_info(stored_path)
        
        return jsonify({
            'message': 'Package uploaded successfully', 
            'filename': filename,
            'size': len(file_data),
            'package_info': package_info
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

@app.route('/search')
def search_packages():
    """Search packages"""
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify({'packages': []})
    
    results = package_manager.search_packages(query)
    return jsonify({'packages': results})

@app.route('/api/packages')
def api_packages():
    """API endpoint to get all packages"""
    packages = package_manager.get_all_packages()
    return jsonify(packages)

@app.route('/api/packages/<package_name>')
def api_package_info(package_name):
    """API endpoint to get package information"""
    packages = package_manager.get_all_packages()
    package_name_lower = package_name.lower()
    
    if package_name_lower not in packages:
        return jsonify({'error': 'Package not found'}), 404
    
    return jsonify({
        'name': package_name,
        'files': packages[package_name_lower]
    })

@app.route('/api/stats')
def api_stats():
    """API endpoint to get server statistics"""
    stats = package_manager.get_package_stats()
    return jsonify(stats)

# Admin routes (require authentication)
if config.auth_enabled:
    @app.route('/admin')
    @auth.require_auth(admin_required=True)
    def admin_panel():
        """Admin panel"""
        users = user_manager.list_users()
        stats = package_manager.get_package_stats()
        return render_template_string(ADMIN_TEMPLATE, users=users, stats=stats)
    
    @app.route('/admin/users', methods=['GET', 'POST'])
    @auth.require_auth(admin_required=True)
    def admin_users():
        """Manage users"""
        if request.method == 'POST':
            action = request.json.get('action')
            username = request.json.get('username')
            
            if action == 'create':
                password = request.json.get('password')
                email = request.json.get('email', '')
                is_admin = request.json.get('is_admin', False)
                
                try:
                    user_manager.create_user(username, password, email, is_admin)
                    return jsonify({'success': True, 'message': 'User created'})
                except ValueError as e:
                    return jsonify({'success': False, 'error': str(e)}), 400
            
            elif action == 'deactivate':
                if user_manager.deactivate_user(username):
                    return jsonify({'success': True, 'message': 'User deactivated'})
                return jsonify({'success': False, 'error': 'User not found'}), 404
            
            elif action == 'activate':
                if user_manager.activate_user(username):
                    return jsonify({'success': True, 'message': 'User activated'})
                return jsonify({'success': False, 'error': 'User not found'}), 404
        
        users = user_manager.list_users()
        return jsonify(users)
    
    @app.route('/api/tokens', methods=['GET', 'POST', 'DELETE'])
    @auth.require_auth()
    def api_tokens():
        """Manage API tokens"""
        username = request.authenticated_user
        
        if request.method == 'POST':
            name = request.json.get('name', f'Token for {username}')
            expires_days = request.json.get('expires_days')
            
            token = user_manager.create_token(username, name, expires_days)
            return jsonify({'token': token, 'message': 'Token created'})
        
        elif request.method == 'DELETE':
            token = request.json.get('token')
            if user_manager.revoke_token(token):
                return jsonify({'message': 'Token revoked'})
            return jsonify({'error': 'Token not found'}), 404
        
        tokens = user_manager.list_tokens(username)
        return jsonify({'tokens': tokens})

# HTML Templates
ENHANCED_INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PyPI Clone</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            margin: 0; padding: 20px; background-color: #f8f9fa; 
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { 
            text-align: center; margin-bottom: 40px; 
            background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header h1 { margin: 0; color: #2c3e50; font-size: 2.5em; }
        .header p { color: #7f8c8d; margin: 10px 0 0; }
        
        .stats { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; margin-bottom: 30px; 
        }
        .stat-card { 
            background: white; padding: 20px; border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center;
        }
        .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        
        .upload-section { 
            margin-bottom: 30px; padding: 25px; background: white; 
            border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .upload-section h3 { margin-top: 0; color: #2c3e50; }
        .upload-section code { 
            background: #ecf0f1; padding: 10px; border-radius: 4px; 
            display: block; margin: 10px 0; font-family: Monaco, monospace;
        }
        
        .search-section { 
            margin-bottom: 30px; background: white; padding: 25px; 
            border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .search-box { display: flex; gap: 10px; }
        .search-box input { 
            flex: 1; padding: 12px; border: 1px solid #ddd; 
            border-radius: 4px; font-size: 16px;
        }
        .search-box button { 
            padding: 12px 24px; background: #3498db; color: white; 
            border: none; border-radius: 4px; cursor: pointer;
        }
        .search-box button:hover { background: #2980b9; }
        
        .package-list { 
            display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); 
            gap: 20px; 
        }
        .package-card { 
            background: white; padding: 20px; border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); transition: transform 0.2s;
        }
        .package-card:hover { transform: translateY(-2px); }
        .package-name { 
            font-size: 18px; font-weight: 600; margin-bottom: 8px;
        }
        .package-name a { color: #3498db; text-decoration: none; }
        .package-name a:hover { text-decoration: underline; }
        .package-version { 
            background: #ecf0f1; color: #2c3e50; padding: 4px 8px; 
            border-radius: 4px; font-size: 12px; display: inline-block;
        }
        .package-summary { 
            margin: 12px 0; color: #555; line-height: 1.4;
        }
        .package-meta { 
            font-size: 12px; color: #7f8c8d; margin-top: 12px;
            padding-top: 12px; border-top: 1px solid #ecf0f1;
        }
        
        .no-packages { 
            text-align: center; color: #7f8c8d; margin: 50px 0;
            background: white; padding: 40px; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .admin-link {
            position: fixed; top: 20px; right: 20px; 
            background: #e74c3c; color: white; padding: 10px 15px; 
            border-radius: 4px; text-decoration: none; font-size: 14px;
        }
        .admin-link:hover { background: #c0392b; color: white; }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .search-box { flex-direction: column; }
            .package-list { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="container">
        {% if auth_enabled %}
        <a href="/admin" class="admin-link">Admin Panel</a>
        {% endif %}
        
        <div class="header">
            <h1>PyPI Clone</h1>
            <p>A Python Package Index server for your organization</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_packages }}</div>
                <div class="stat-label">Packages</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_files }}</div>
                <div class="stat-label">Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_size_mb }}</div>
                <div class="stat-label">MB Total</div>
            </div>
        </div>
        
        <div class="upload-section">
            <h3>📦 Upload Packages</h3>
            <p>Use <strong>twine</strong> to upload your Python packages:</p>
            <code>twine upload --repository-url http://{{ request.host }}/upload dist/*</code>
            {% if auth_enabled %}
            <p><strong>🔐 Authentication required:</strong> username: <code>admin</code>, password: <code>admin</code></p>
            {% endif %}
        </div>
        
        <div class="search-section">
            <h3>🔍 Search Packages</h3>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search packages by name or description...">
                <button onclick="searchPackages()">Search</button>
            </div>
        </div>
        
        <div id="packageList" class="package-list">
            {% if packages %}
                {% for name, files in packages.items() %}
                    {% set latest = files[0] %}
                    <div class="package-card">
                        <div class="package-name">
                            <a href="/simple/{{ name }}/">{{ name }}</a>
                        </div>
                        <span class="package-version">{{ latest.version or 'unknown' }}</span>
                        <div class="package-summary">
                            {{ latest.summary or 'No description available' }}
                        </div>
                        <div class="package-meta">
                            📁 {{ files|length }} file{{ 's' if files|length != 1 else '' }} • 
                            📅 Latest: {{ latest.upload_time.strftime('%Y-%m-%d') if latest.upload_time else 'unknown' }} •
                            📏 {{ "%.1f"|format(latest.size / 1024) }} KB
                        </div>
                    </div>
                {% endfor %}
            {% else %}
                <div class="no-packages">
                    <h3>📦 No packages yet</h3>
                    <p>Upload some packages to get started!</p>
                </div>
            {% endif %}
        </div>
    </div>
    
    <script>
        function searchPackages() {
            const query = document.getElementById('searchInput').value.trim();
            if (query.length < 2) {
                location.reload();
                return;
            }
            
            fetch(`/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    const packageList = document.getElementById('packageList');
                    packageList.innerHTML = '';
                    
                    if (data.packages.length === 0) {
                        packageList.innerHTML = `
                            <div class="no-packages">
                                <h3>🔍 No packages found</h3>
                                <p>Try searching with different keywords.</p>
                            </div>
                        `;
                        return;
                    }
                    
                    data.packages.forEach(pkg => {
                        const card = document.createElement('div');
                        card.className = 'package-card';
                        card.innerHTML = `
                            <div class="package-name">
                                <a href="/simple/${pkg.name}/">${pkg.name}</a>
                            </div>
                            <span class="package-version">${pkg.latest_version}</span>
                            <div class="package-summary">${pkg.summary || 'No description available'}</div>
                            <div class="package-meta">
                                📁 ${pkg.versions.length} version${pkg.versions.length !== 1 ? 's' : ''} • 
                                👤 ${pkg.author || 'Unknown author'}
                            </div>
                        `;
                        packageList.appendChild(card);
                    });
                })
                .catch(err => {
                    console.error('Search failed:', err);
                });
        }
        
        // Enable search on Enter key
        document.getElementById('searchInput').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                searchPackages();
            }
        });
    </script>
</body>
</html>
"""

ADMIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PyPI Clone - Admin Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; 
            margin: 0; padding: 20px; background-color: #f8f9fa; 
        }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { 
            background: white; padding: 30px; border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px;
        }
        .header h1 { margin: 0; color: #2c3e50; }
        .nav { margin-top: 20px; }
        .nav a { 
            display: inline-block; padding: 10px 20px; margin-right: 10px; 
            background: #3498db; color: white; text-decoration: none; border-radius: 4px;
        }
        .nav a:hover { background: #2980b9; }
        
        .stats { 
            display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
            gap: 20px; margin-bottom: 30px; 
        }
        .stat-card { 
            background: white; padding: 20px; border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center;
        }
        .stat-number { font-size: 2em; font-weight: bold; color: #3498db; }
        .stat-label { color: #7f8c8d; margin-top: 5px; }
        
        .section { 
            background: white; padding: 25px; border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 30px;
        }
        .section h2 { margin-top: 0; color: #2c3e50; }
        
        table { width: 100%; border-collapse: collapse; }
        th, td { padding: 12px; text-align: left; border-bottom: 1px solid #ecf0f1; }
        th { background: #f8f9fa; font-weight: 600; }
        
        .btn { 
            padding: 8px 16px; border: none; border-radius: 4px; 
            cursor: pointer; text-decoration: none; display: inline-block;
        }
        .btn-primary { background: #3498db; color: white; }
        .btn-success { background: #27ae60; color: white; }
        .btn-danger { background: #e74c3c; color: white; }
        .btn-warning { background: #f39c12; color: white; }
        .btn:hover { opacity: 0.8; }
        
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; font-weight: 600; }
        .form-group input { 
            width: 100%; padding: 10px; border: 1px solid #ddd; 
            border-radius: 4px; font-size: 14px;
        }
        .form-group input[type="checkbox"] { width: auto; }
        
        .status-active { color: #27ae60; font-weight: bold; }
        .status-inactive { color: #e74c3c; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🛠️ Admin Panel</h1>
            <div class="nav">
                <a href="/">← Back to Main</a>
                <a href="/api/stats">API Stats</a>
            </div>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_packages }}</div>
                <div class="stat-label">Packages</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_files }}</div>
                <div class="stat-label">Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ stats.total_size_mb }}</div>
                <div class="stat-label">MB Total</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{{ users|length }}</div>
                <div class="stat-label">Users</div>
            </div>
        </div>
        
        <div class="section">
            <h2>👥 User Management</h2>
            
            <div style="margin-bottom: 20px;">
                <button class="btn btn-primary" onclick="showCreateUserForm()">+ Create User</button>
            </div>
            
            <div id="createUserForm" style="display: none; margin-bottom: 20px; padding: 20px; background: #f8f9fa; border-radius: 4px;">
                <h3>Create New User</h3>
                <div class="form-group">
                    <label>Username:</label>
                    <input type="text" id="newUsername" required>
                </div>
                <div class="form-group">
                    <label>Password:</label>
                    <input type="password" id="newPassword" required>
                </div>
                <div class="form-group">
                    <label>Email:</label>
                    <input type="email" id="newEmail">
                </div>
                <div class="form-group">
                    <label>
                        <input type="checkbox" id="newIsAdmin"> Is Admin
                    </label>
                </div>
                <button class="btn btn-success" onclick="createUser()">Create</button>
                <button class="btn" onclick="hideCreateUserForm()" style="background: #95a5a6; color: white;">Cancel</button>
            </div>
            
            <table>
                <thead>
                    <tr>
                        <th>Username</th>
                        <th>Email</th>
                        <th>Admin</th>
                        <th>Created</th>
                        <th>Last Login</th>
                        <th>Status</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    {% for username, user in users.items() %}
                    <tr>
                        <td><strong>{{ username }}</strong></td>
                        <td>{{ user.email or '-' }}</td>
                        <td>{{ '✅' if user.is_admin else '❌' }}</td>
                        <td>{{ user.created_at[:10] if user.created_at else '-' }}</td>
                        <td>{{ user.last_login[:10] if user.last_login else 'Never' }}</td>
                        <td>
                            {% if user.active %}
                                <span class="status-active">Active</span>
                            {% else %}
                                <span class="status-inactive">Inactive</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if user.active %}
                                <button class="btn btn-warning" onclick="deactivateUser('{{ username }}')">Deactivate</button>
                            {% else %}
                                <button class="btn btn-success" onclick="activateUser('{{ username }}')">Activate</button>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
    
    <script>
        function showCreateUserForm() {
            document.getElementById('createUserForm').style.display = 'block';
        }
        
        function hideCreateUserForm() {
            document.getElementById('createUserForm').style.display = 'none';
            // Clear form
            document.getElementById('newUsername').value = '';
            document.getElementById('newPassword').value = '';
            document.getElementById('newEmail').value = '';
            document.getElementById('newIsAdmin').checked = false;
        }
        
        async function createUser() {
            const username = document.getElementById('newUsername').value.trim();
            const password = document.getElementById('newPassword').value;
            const email = document.getElementById('newEmail').value.trim();
            const isAdmin = document.getElementById('newIsAdmin').checked;
            
            if (!username || !password) {
                alert('Username and password are required');
                return;
            }
            
            try {
                const response = await fetch('/admin/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'create',
                        username: username,
                        password: password,
                        email: email,
                        is_admin: isAdmin
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    alert('User created successfully');
                    location.reload();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('Error creating user: ' + err.message);
            }
        }
        
        async function deactivateUser(username) {
            if (!confirm(`Are you sure you want to deactivate user "${username}"?`)) {
                return;
            }
            
            try {
                const response = await fetch('/admin/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'deactivate',
                        username: username
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    location.reload();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('Error deactivating user: ' + err.message);
            }
        }
        
        async function activateUser(username) {
            try {
                const response = await fetch('/admin/users', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        action: 'activate',
                        username: username
                    })
                });
                
                const result = await response.json();
                
                if (result.success) {
                    location.reload();
                } else {
                    alert('Error: ' + result.error);
                }
            } catch (err) {
                alert('Error activating user: ' + err.message);
            }
        }
    </script>
</body>
</html>
"""

def main():
    """Main entry point"""
    print(f"🚀 Starting PyPI Clone server...")
    print(f"📁 Package directory: {os.path.abspath(config.data_dir)}")
    print(f"🔐 Authentication: {'Enabled' if config.auth_enabled else 'Disabled'}")
    print(f"🌐 Server URL: http://{config.host}:{config.port}")
    
    if config.auth_enabled:
        print(f"👤 Default admin credentials: admin / admin")
    
    try:
        app.run(host=config.host, port=config.port, debug=config.debug)
    except KeyboardInterrupt:
        print("\n👋 Server stopped")

if __name__ == '__main__':
    main()
