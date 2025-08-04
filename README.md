# PyPI Clone

A simple PyPI (Python Package Index) clone server that supports package upload, download, and management.

## Features

- Package upload and download
- Package search and browsing
- Simple web interface
- Basic authentication
- Package versioning
- RESTful API

## Quick Start

1. Clone the repository
2. Run the setup script:
```bash
chmod +x local-deploy.sh
./local-deploy.sh
```

3. Start the server:
```bash
./venv/bin/python server.py
```

4. The server will run on `http://localhost:8080`

## Manual Installation

If you prefer to set up manually:

1. Create virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Start the server:
```bash
python server.py
```

## API Endpoints

- `GET /` - Web interface
- `GET /simple/` - Package index (pip compatible)
- `GET /simple/{package}/` - Package versions
- `POST /upload` - Upload package (requires authentication)
- `GET /packages/{filename}` - Download package
- `GET /search` - Search packages

## Configuration

The server can be configured through environment variables:
- `PYPI_HOST` - Host to bind to (default: localhost)
- `PYPI_PORT` - Port to bind to (default: 8080)
- `PYPI_DATA_DIR` - Directory to store packages (default: ./packages)
- `PYPI_AUTH` - Enable authentication (default: False)

## Authentication

When authentication is enabled, use the following credentials:
- Username: admin
- Password: admin

To upload packages with authentication:
```bash
twine upload --repository-url http://localhost:8080/upload --username admin --password admin dist/*
```
