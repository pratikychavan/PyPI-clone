#!/usr/bin/env python3
"""
PyPI Clone Server

A simple PyPI (Python Package Index) clone that supports:
- Package upload and download
- Package search and browsing
- Simple web interface
- Basic authentication
- Package versioning
"""

import os
import re
import json
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from urllib.parse import unquote
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from flask import Flask, request, jsonify, render_template_string, send_file, abort, redirect, url_for, flash
import zipfile
import tarfile

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# Configuration
PYPI_HOST = os.getenv('PYPI_HOST', 'localhost')
PYPI_PORT = int(os.getenv('PYPI_PORT', 8080))
PYPI_DATA_DIR = os.getenv('PYPI_DATA_DIR', './packages')
PYPI_AUTH = os.getenv('PYPI_AUTH', 'False').lower() == 'true'

# Create packages directory
os.makedirs(PYPI_DATA_DIR, exist_ok=True)

# Simple user store (in production, use a proper database)
USERS = {
    'admin': generate_password_hash('admin')
}

def authenticate(username, password):
    """Simple authentication check"""
    if not PYPI_AUTH:
        return True
    user_hash = USERS.get(username)
    return user_hash and check_password_hash(user_hash, password)

def get_package_metadata(filepath):
    """Extract metadata from package file"""
    try:
        if filepath.endswith('.whl'):
            return get_wheel_metadata(filepath)
        elif filepath.endswith('.tar.gz'):
            return get_sdist_metadata(filepath)
    except Exception as e:
        print(f"Error extracting metadata from {filepath}: {e}")
    return {}

def get_wheel_metadata(filepath):
    """Extract metadata from wheel file"""
    metadata = {}
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            for name in zf.namelist():
                if name.endswith('.dist-info/METADATA'):
                    with zf.open(name) as f:
                        content = f.read().decode('utf-8')
                        metadata = parse_metadata(content)
                    break
    except Exception as e:
        print(f"Error reading wheel metadata: {e}")
    return metadata

def get_sdist_metadata(filepath):
    """Extract metadata from source distribution"""
    metadata = {}
    try:
        with tarfile.open(filepath, 'r:gz') as tf:
            for member in tf.getmembers():
                if member.name.endswith('/PKG-INFO'):
                    f = tf.extractfile(member)
                    if f:
                        content = f.read().decode('utf-8')
                        metadata = parse_metadata(content)
                    break
    except Exception as e:
        print(f"Error reading sdist metadata: {e}")
    return metadata

def parse_metadata(content):
    """Parse package metadata from PKG-INFO format"""
    metadata = {}
    lines = content.split('\n')
    
    for line in lines:
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            if key == 'Name':
                metadata['name'] = value
            elif key == 'Version':
                metadata['version'] = value
            elif key == 'Summary':
                metadata['summary'] = value
            elif key == 'Author':
                metadata['author'] = value
            elif key == 'Author-email':
                metadata['author_email'] = value
            elif key == 'Home-page':
                metadata['home_page'] = value
            elif key == 'Description':
                # Description might span multiple lines
                description_lines = [value]
                continue
        elif line.startswith('        ') and 'description_lines' in locals():
            description_lines.append(line.strip())
    
    if 'description_lines' in locals():
        metadata['description'] = '\n'.join(description_lines)
    
    return metadata

def get_package_list():
    """Get list of all packages"""
    packages = {}
    package_dir = Path(PYPI_DATA_DIR)
    
    for file_path in package_dir.rglob('*'):
        if file_path.is_file() and (file_path.suffix in ['.whl', '.gz']):
            # Extract package name from filename
            filename = file_path.name
            if filename.endswith('.whl'):
                # wheel format: {name}-{version}-{build tag}-{language tag}-{abi tag}-{platform tag}.whl
                name = filename.split('-')[0]
            elif filename.endswith('.tar.gz'):
                # sdist format: {name}-{version}.tar.gz
                name = '-'.join(filename.replace('.tar.gz', '').split('-')[:-1])
            else:
                continue
            
            name = name.lower()
            if name not in packages:
                packages[name] = []
            
            # Get file stats
            stat = file_path.stat()
            package_info = {
                'filename': filename,
                'path': str(file_path.relative_to(package_dir)),
                'size': stat.st_size,
                'upload_time': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'md5_digest': get_file_hash(file_path)
            }
            
            # Add metadata if available
            metadata = get_package_metadata(str(file_path))
            package_info.update(metadata)
            
            packages[name].append(package_info)
    
    return packages

def get_file_hash(filepath):
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception:
        return ""

@app.route('/')
def index():
    """Main web interface"""
    packages = get_package_list()
    return render_template_string(INDEX_TEMPLATE, packages=packages)

@app.route('/simple/')
def simple_index():
    """PyPI simple API - package index"""
    packages = get_package_list()
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
    packages = get_package_list()
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
        html += f'    <a href="/packages/{filename}#md5={md5_hash}">{filename}</a><br>\n'
    
    html += """</body>
</html>"""
    
    return html

@app.route('/packages/<filename>')
def download_package(filename):
    """Download package file"""
    filename = secure_filename(filename)
    file_path = Path(PYPI_DATA_DIR) / filename
    
    # Also check in subdirectories
    if not file_path.exists():
        for file_path in Path(PYPI_DATA_DIR).rglob(filename):
            if file_path.is_file():
                break
        else:
            abort(404)
    
    return send_file(str(file_path), as_attachment=True)

@app.route('/upload', methods=['POST'])
def upload_package():
    """Upload package file"""
    # Check authentication
    auth = request.authorization
    if PYPI_AUTH and (not auth or not authenticate(auth.username, auth.password)):
        return jsonify({'error': 'Authentication required'}), 401
    
    # Check if file was uploaded
    if 'content' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['content']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    # Validate file type
    if not (file.filename.endswith('.whl') or file.filename.endswith('.tar.gz')):
        return jsonify({'error': 'Only .whl and .tar.gz files are supported'}), 400
    
    # Save file
    filename = secure_filename(file.filename)
    file_path = Path(PYPI_DATA_DIR) / filename
    
    # Create directory if it doesn't exist
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if file already exists
    if file_path.exists():
        return jsonify({'error': 'File already exists'}), 409
    
    file.save(str(file_path))
    
    return jsonify({'message': 'Package uploaded successfully', 'filename': filename}), 200

@app.route('/search')
def search_packages():
    """Search packages"""
    query = request.args.get('q', '').lower()
    packages = get_package_list()
    
    if not query:
        return jsonify({'packages': []})
    
    results = []
    for name, files in packages.items():
        if query in name.lower():
            # Get latest version
            latest_file = max(files, key=lambda x: x.get('upload_time', ''))
            results.append({
                'name': name,
                'version': latest_file.get('version', 'unknown'),
                'summary': latest_file.get('summary', ''),
                'author': latest_file.get('author', ''),
                'home_page': latest_file.get('home_page', '')
            })
    
    return jsonify({'packages': results})

@app.route('/api/packages')
def api_packages():
    """API endpoint to get all packages"""
    packages = get_package_list()
    return jsonify(packages)

@app.route('/api/packages/<package_name>')
def api_package_info(package_name):
    """API endpoint to get package information"""
    packages = get_package_list()
    package_name_lower = package_name.lower()
    
    if package_name_lower not in packages:
        return jsonify({'error': 'Package not found'}), 404
    
    return jsonify({
        'name': package_name,
        'files': packages[package_name_lower]
    })

# HTML Templates
INDEX_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>PyPI Clone</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .header { text-align: center; margin-bottom: 40px; }
        .search-box { text-align: center; margin-bottom: 30px; }
        .search-box input { padding: 10px; width: 300px; }
        .search-box button { padding: 10px 20px; }
        .package-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .package-card { border: 1px solid #ddd; padding: 20px; border-radius: 5px; }
        .package-name { font-size: 18px; font-weight: bold; color: #0066cc; }
        .package-version { color: #666; }
        .package-summary { margin-top: 10px; color: #333; }
        .no-packages { text-align: center; color: #666; margin-top: 50px; }
        .upload-section { margin-bottom: 30px; padding: 20px; background-color: #f5f5f5; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>PyPI Clone</h1>
        <p>A simple Python Package Index server</p>
    </div>
    
    <div class="upload-section">
        <h3>Upload Package</h3>
        <p>To upload packages, use twine:</p>
        <code>twine upload --repository-url http://{{ request.host }}/upload dist/*</code>
        {% if config.get('PYPI_AUTH') %}
        <p><strong>Authentication required:</strong> username: admin, password: admin</p>
        {% endif %}
    </div>
    
    <div class="search-box">
        <input type="text" id="searchInput" placeholder="Search packages..." onkeyup="searchPackages()">
        <button onclick="searchPackages()">Search</button>
    </div>
    
    <div id="packageList" class="package-list">
        {% if packages %}
            {% for name, files in packages.items() %}
                {% set latest = files|max(attribute='upload_time') %}
                <div class="package-card">
                    <div class="package-name">
                        <a href="/simple/{{ name }}/">{{ name }}</a>
                    </div>
                    <div class="package-version">{{ latest.version or 'unknown' }}</div>
                    <div class="package-summary">{{ latest.summary or 'No description available' }}</div>
                    <div style="margin-top: 10px; font-size: 12px; color: #999;">
                        Files: {{ files|length }}, Latest: {{ latest.upload_time }}
                    </div>
                </div>
            {% endfor %}
        {% else %}
            <div class="no-packages">
                <p>No packages available. Upload some packages to get started!</p>
            </div>
        {% endif %}
    </div>
    
    <script>
        function searchPackages() {
            const query = document.getElementById('searchInput').value;
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
                        packageList.innerHTML = '<div class="no-packages"><p>No packages found.</p></div>';
                        return;
                    }
                    
                    data.packages.forEach(pkg => {
                        const card = document.createElement('div');
                        card.className = 'package-card';
                        card.innerHTML = `
                            <div class="package-name">
                                <a href="/simple/${pkg.name}/">${pkg.name}</a>
                            </div>
                            <div class="package-version">${pkg.version}</div>
                            <div class="package-summary">${pkg.summary}</div>
                        `;
                        packageList.appendChild(card);
                    });
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

if __name__ == '__main__':
    print(f"Starting PyPI Clone server on http://{PYPI_HOST}:{PYPI_PORT}")
    print(f"Package directory: {os.path.abspath(PYPI_DATA_DIR)}")
    print(f"Authentication: {'Enabled' if PYPI_AUTH else 'Disabled'}")
    
    app.run(host=PYPI_HOST, port=PYPI_PORT, debug=True)
