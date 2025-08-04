#!/usr/bin/env python3
"""
Authentication and user management for PyPI Clone
"""

import json
import hashlib
import secrets
from pathlib import Path
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

class UserManager:
    """Manages users and authentication"""
    
    def __init__(self, user_file='users.json'):
        self.user_file = Path(user_file)
        self.users = {}
        self.tokens = {}  # API tokens
        self.load_users()
    
    def load_users(self):
        """Load users from file"""
        if self.user_file.exists():
            try:
                with open(self.user_file, 'r') as f:
                    data = json.load(f)
                    self.users = data.get('users', {})
                    self.tokens = data.get('tokens', {})
            except Exception as e:
                print(f"Error loading users: {e}")
                self.users = {}
                self.tokens = {}
        
        # Ensure default admin user exists
        if not self.users:
            self.create_user('admin', 'admin', is_admin=True)
    
    def save_users(self):
        """Save users to file"""
        data = {
            'users': self.users,
            'tokens': self.tokens
        }
        try:
            with open(self.user_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving users: {e}")
    
    def create_user(self, username, password, email=None, is_admin=False):
        """Create a new user"""
        if username in self.users:
            raise ValueError(f"User {username} already exists")
        
        self.users[username] = {
            'password_hash': generate_password_hash(password),
            'email': email or '',
            'is_admin': is_admin,
            'created_at': datetime.now().isoformat(),
            'last_login': None,
            'active': True
        }
        self.save_users()
        return True
    
    def authenticate(self, username, password):
        """Authenticate user with username and password"""
        user = self.users.get(username)
        if not user or not user.get('active', True):
            return False
        
        if check_password_hash(user['password_hash'], password):
            # Update last login
            user['last_login'] = datetime.now().isoformat()
            self.save_users()
            return True
        
        return False
    
    def authenticate_token(self, token):
        """Authenticate user with API token"""
        token_info = self.tokens.get(token)
        if not token_info:
            return None
        
        # Check if token is expired
        if token_info.get('expires_at'):
            expires_at = datetime.fromisoformat(token_info['expires_at'])
            if datetime.now() > expires_at:
                del self.tokens[token]
                self.save_users()
                return None
        
        username = token_info['username']
        user = self.users.get(username)
        if user and user.get('active', True):
            return username
        
        return None
    
    def create_token(self, username, name=None, expires_days=None):
        """Create API token for user"""
        if username not in self.users:
            raise ValueError(f"User {username} does not exist")
        
        token = secrets.token_urlsafe(32)
        expires_at = None
        if expires_days:
            expires_at = (datetime.now() + timedelta(days=expires_days)).isoformat()
        
        self.tokens[token] = {
            'username': username,
            'name': name or f"Token for {username}",
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at,
            'last_used': None
        }
        self.save_users()
        return token
    
    def revoke_token(self, token):
        """Revoke an API token"""
        if token in self.tokens:
            del self.tokens[token]
            self.save_users()
            return True
        return False
    
    def list_tokens(self, username):
        """List all tokens for a user"""
        user_tokens = []
        for token, info in self.tokens.items():
            if info['username'] == username:
                user_tokens.append({
                    'token': token[:8] + '...',  # Partial token for security
                    'name': info['name'],
                    'created_at': info['created_at'],
                    'expires_at': info.get('expires_at'),
                    'last_used': info.get('last_used')
                })
        return user_tokens
    
    def change_password(self, username, old_password, new_password):
        """Change user password"""
        if not self.authenticate(username, old_password):
            raise ValueError("Invalid current password")
        
        self.users[username]['password_hash'] = generate_password_hash(new_password)
        self.save_users()
        return True
    
    def is_admin(self, username):
        """Check if user is admin"""
        user = self.users.get(username)
        return user and user.get('is_admin', False)
    
    def list_users(self):
        """List all users (admin only)"""
        return {
            username: {
                'email': user.get('email', ''),
                'is_admin': user.get('is_admin', False),
                'created_at': user.get('created_at'),
                'last_login': user.get('last_login'),
                'active': user.get('active', True)
            }
            for username, user in self.users.items()
        }
    
    def deactivate_user(self, username):
        """Deactivate a user"""
        if username in self.users:
            self.users[username]['active'] = False
            self.save_users()
            return True
        return False
    
    def activate_user(self, username):
        """Activate a user"""
        if username in self.users:
            self.users[username]['active'] = True
            self.save_users()
            return True
        return False

class SimpleAuth:
    """Simple authentication decorator"""
    
    def __init__(self, user_manager):
        self.user_manager = user_manager
    
    def require_auth(self, admin_required=False):
        """Decorator to require authentication"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                from flask import request, jsonify
                
                auth = request.authorization
                token = request.headers.get('Authorization')
                
                username = None
                
                # Try token authentication first
                if token and token.startswith('Bearer '):
                    token = token[7:]  # Remove 'Bearer ' prefix
                    username = self.user_manager.authenticate_token(token)
                
                # Fall back to basic auth
                if not username and auth:
                    if self.user_manager.authenticate(auth.username, auth.password):
                        username = auth.username
                
                if not username:
                    return jsonify({'error': 'Authentication required'}), 401
                
                if admin_required and not self.user_manager.is_admin(username):
                    return jsonify({'error': 'Admin access required'}), 403
                
                # Add username to request context
                request.authenticated_user = username
                return func(*args, **kwargs)
            
            wrapper.__name__ = func.__name__
            return wrapper
        return decorator
