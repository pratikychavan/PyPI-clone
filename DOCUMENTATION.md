# PyPI Clone - Comprehensive Documentation

## Overview

This PyPI Clone is a complete Python Package Index server implementation that provides:

- **Package Management**: Upload, download, and manage Python packages
- **Web Interface**: Modern, responsive web UI for browsing packages
- **Authentication**: User management with API tokens
- **Search**: Full-text search through package names and descriptions
- **PyPI Compatibility**: Works with pip, twine, and other standard tools
- **Admin Panel**: Web-based administration interface
- **REST API**: Complete API for programmatic access
- **CLI Tools**: Command-line interface for server management

## Quick Start

### 1. Installation

```bash
# Clone or download the project
cd pypiserver

# Install dependencies (recommended: use virtual environment)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Start the Server

```bash
# Simple start
python3 server.py

# Or use the startup script
./start.sh

# Or use CLI with options
python3 cli.py start --host 0.0.0.0 --port 8080 --auth
```

### 3. Access the Server

- **Web Interface**: http://localhost:8080
- **PyPI Simple API**: http://localhost:8080/simple/
- **Admin Panel**: http://localhost:8080/admin (if auth enabled)

## Configuration

### Environment Variables

- `PYPI_HOST`: Host to bind to (default: localhost)
- `PYPI_PORT`: Port to bind to (default: 8080)
- `PYPI_DATA_DIR`: Directory to store packages (default: ./packages)
- `PYPI_AUTH`: Enable authentication (default: False)
- `PYPI_DEBUG`: Enable debug mode (default: True)
- `PYPI_SECRET_KEY`: Secret key for sessions

### Configuration File

Copy `pypi.conf.sample` to `pypi.conf` and modify:

```ini
[server]
host = localhost
port = 8080
data_dir = ./packages
debug = true
secret_key = your-secret-key-here
max_file_size = 104857600

[auth]
enabled = false
```

## Package Management

### Uploading Packages

Use `twine` to upload packages:

```bash
# Without authentication
twine upload --repository-url http://localhost:8080/upload dist/*

# With authentication
twine upload --repository-url http://localhost:8080/upload \
  --username admin --password admin dist/*
```

### Installing Packages

Configure pip to use your PyPI server:

```bash
# Install from your PyPI server
pip install --index-url http://localhost:8080/simple/ package-name

# Use as extra index
pip install --extra-index-url http://localhost:8080/simple/ package-name
```

### Create pip configuration

Create `~/.pip/pip.conf` (Linux/Mac) or `%APPDATA%\pip\pip.ini` (Windows):

```ini
[global]
extra-index-url = http://localhost:8080/simple/
```

## User Management

### Default Credentials

When authentication is enabled:
- Username: `admin`
- Password: `admin`

**Change these in production!**

### CLI User Management

```bash
# Create user
python3 cli.py user create --username newuser --password secret --email user@example.com

# List users
python3 cli.py user list

# Create API token
python3 cli.py user token --username admin --token-name "CI/CD Token" --expires-days 30

# Deactivate user
python3 cli.py user delete --username olduser
```

### Web Admin Panel

Access http://localhost:8080/admin (requires admin authentication) to:
- Manage users
- View statistics
- Monitor uploads

## API Reference

### Package APIs

```bash
# List all packages
GET /api/packages

# Get package information
GET /api/packages/{package-name}

# Search packages
GET /search?q={query}

# Server statistics
GET /api/stats
```

### Upload API

```bash
# Upload package (multipart/form-data)
POST /upload
Content-Type: multipart/form-data
Authorization: Basic {base64(username:password)}

# Form field: content (file)
```

### Authentication APIs

```bash
# Create API token
POST /api/tokens
Authorization: Basic {base64(username:password)}
Content-Type: application/json
{
  "name": "Token Name",
  "expires_days": 30
}

# List tokens
GET /api/tokens
Authorization: Basic {base64(username:password)}

# Revoke token
DELETE /api/tokens
Authorization: Basic {base64(username:password)}
Content-Type: application/json
{
  "token": "token-to-revoke"
}
```

## CLI Reference

### Server Management

```bash
# Start server
python3 cli.py start [options]

# Initialize configuration
python3 cli.py init [--config pypi.conf] [--force]

# Show statistics
python3 cli.py stats
```

### Package Management

```bash
# List packages
python3 cli.py packages list

# Search packages
python3 cli.py packages search --query "search term"

# Package information
python3 cli.py packages info --package-name "package-name"
```

### User Management

```bash
# Create user
python3 cli.py user create [--username] [--password] [--email] [--admin]

# List users
python3 cli.py user list

# Delete user
python3 cli.py user delete [--username]

# Create API token
python3 cli.py user token [--username] [--token-name] [--expires-days]
```

## Security Considerations

### Production Deployment

1. **Change default credentials**:
   ```bash
   python3 cli.py user create --username myadmin --password strongpassword --admin
   ```

2. **Use HTTPS**: Deploy behind a reverse proxy with SSL
3. **Set strong secret key**: Change `secret_key` in configuration
4. **Enable authentication**: Set `PYPI_AUTH=true`
5. **Limit file sizes**: Adjust `max_file_size` as needed
6. **Regular backups**: Backup packages directory and user database

### Authentication

- Basic HTTP authentication for uploads
- API tokens for automated access
- Admin-only functions protected
- Session-based web authentication

## Deployment Options

### Systemd Service

Create `/etc/systemd/system/pypi-clone.service`:

```ini
[Unit]
Description=PyPI Clone Server
After=network.target

[Service]
Type=simple
User=pypi
WorkingDirectory=/opt/pypi-clone
ExecStart=/opt/pypi-clone/venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name pypi.yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Testing

### Automated Tests

```bash
# Run all tests
python3 test_server.py

# Test with authentication
python3 test_server.py --username admin --password admin

# Test custom URL
python3 test_server.py --url http://example.com:8080
```

### Manual Testing

1. **Upload a package**:
   ```bash
   twine upload --repository-url http://localhost:8080/upload dist/*
   ```

2. **Install a package**:
   ```bash
   pip install --index-url http://localhost:8080/simple/ your-package
   ```

3. **Search packages**:
   - Use web interface
   - Use API: `curl http://localhost:8080/search?q=package-name`

## Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   python3 cli.py start --port 8081
   ```

2. **Permission denied for packages directory**:
   ```bash
   chmod 755 packages/
   ```

3. **Upload fails with 413 error**:
   - Increase `max_file_size` in configuration
   - Check available disk space

4. **Authentication issues**:
   - Verify username/password
   - Check if authentication is enabled
   - Use API tokens for automated access

### Logs and Debugging

- Enable debug mode: `PYPI_DEBUG=true`
- Check console output for errors
- Use `python3 cli.py stats` to verify server state

## Contributing

This PyPI Clone is designed to be:
- Easy to understand and modify
- Well-documented
- Modular and extensible

Key modules:
- `server.py`: Main Flask application
- `package_manager.py`: Package handling logic
- `auth.py`: Authentication and user management
- `config.py`: Configuration management
- `cli.py`: Command-line interface

## License

This project is provided as-is for educational and internal use purposes.
