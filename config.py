#!/usr/bin/env python3
"""
Configuration and utilities for PyPI Clone server
"""

import os
import configparser
from pathlib import Path

class Config:
    """Configuration class for PyPI server"""
    
    def __init__(self, config_file=None):
        self.config_file = config_file or 'pypi.conf'
        self.load_config()
    
    def load_config(self):
        """Load configuration from file and environment variables"""
        # Default configuration
        self.host = 'localhost'
        self.port = 8080
        self.data_dir = './packages'
        self.auth_enabled = False
        self.debug = True
        self.secret_key = 'change-this-in-production'
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        
        # Load from config file if exists
        if os.path.exists(self.config_file):
            config = configparser.ConfigParser()
            config.read(self.config_file)
            
            if 'server' in config:
                server_config = config['server']
                self.host = server_config.get('host', self.host)
                self.port = server_config.getint('port', self.port)
                self.data_dir = server_config.get('data_dir', self.data_dir)
                self.debug = server_config.getboolean('debug', self.debug)
                self.secret_key = server_config.get('secret_key', self.secret_key)
                self.max_file_size = server_config.getint('max_file_size', self.max_file_size)
            
            if 'auth' in config:
                auth_config = config['auth']
                self.auth_enabled = auth_config.getboolean('enabled', self.auth_enabled)
        
        # Override with environment variables
        self.host = os.getenv('PYPI_HOST', self.host)
        self.port = int(os.getenv('PYPI_PORT', self.port))
        self.data_dir = os.getenv('PYPI_DATA_DIR', self.data_dir)
        self.auth_enabled = os.getenv('PYPI_AUTH', str(self.auth_enabled)).lower() == 'true'
        self.debug = os.getenv('PYPI_DEBUG', str(self.debug)).lower() == 'true'
        self.secret_key = os.getenv('PYPI_SECRET_KEY', self.secret_key)
        
        # Ensure data directory exists
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)
    
    def save_config(self):
        """Save current configuration to file"""
        config = configparser.ConfigParser()
        
        config['server'] = {
            'host': self.host,
            'port': str(self.port),
            'data_dir': self.data_dir,
            'debug': str(self.debug),
            'secret_key': self.secret_key,
            'max_file_size': str(self.max_file_size)
        }
        
        config['auth'] = {
            'enabled': str(self.auth_enabled)
        }
        
        with open(self.config_file, 'w') as f:
            config.write(f)

def create_sample_config():
    """Create a sample configuration file"""
    config_content = """[server]
# Host to bind to
host = localhost

# Port to bind to
port = 8080

# Directory to store packages
data_dir = ./packages

# Enable debug mode
debug = true

# Secret key for sessions (change in production!)
secret_key = change-this-in-production

# Maximum file size in bytes (100MB)
max_file_size = 104857600

[auth]
# Enable authentication for uploads
enabled = false
"""
    
    with open('pypi.conf.sample', 'w') as f:
        f.write(config_content)
    
    print("Sample configuration file created: pypi.conf.sample")

if __name__ == '__main__':
    create_sample_config()
