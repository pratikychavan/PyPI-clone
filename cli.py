#!/usr/bin/env python3
"""
Command-line interface for PyPI Clone server management
"""

import os
import sys
import argparse
import getpass
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config, create_sample_config
from package_manager import PackageManager
from auth import UserManager

def cmd_start(args):
    """Start the PyPI server"""
    # Set environment variables from command line args
    if args.host:
        os.environ['PYPI_HOST'] = args.host
    if args.port:
        os.environ['PYPI_PORT'] = str(args.port)
    if args.data_dir:
        os.environ['PYPI_DATA_DIR'] = args.data_dir
    if args.auth:
        os.environ['PYPI_AUTH'] = 'true'
    if args.debug:
        os.environ['PYPI_DEBUG'] = 'true'
    
    # Import and start server
    from server import main
    main()

def cmd_init(args):
    """Initialize PyPI server configuration"""
    config_file = args.config or 'pypi.conf'
    
    if Path(config_file).exists() and not args.force:
        print(f"Configuration file {config_file} already exists. Use --force to overwrite.")
        return 1
    
    # Create sample config
    create_sample_config()
    print(f"Created sample configuration: pypi.conf.sample")
    print("Copy and modify it to create your configuration.")
    
    return 0

def cmd_user(args):
    """User management commands"""
    user_manager = UserManager(args.user_file or 'users.json')
    
    if args.user_action == 'create':
        username = args.username or input("Username: ")
        password = args.password or getpass.getpass("Password: ")
        email = args.email or input("Email (optional): ") or None
        is_admin = args.admin
        
        try:
            user_manager.create_user(username, password, email, is_admin)
            print(f"User '{username}' created successfully.")
            return 0
        except ValueError as e:
            print(f"Error: {e}")
            return 1
    
    elif args.user_action == 'list':
        users = user_manager.list_users()
        print(f"{'Username':<20} {'Email':<30} {'Admin':<8} {'Active':<8} {'Created'}")
        print("-" * 80)
        for username, user in users.items():
            admin_str = "Yes" if user.get('is_admin') else "No"
            active_str = "Yes" if user.get('active', True) else "No"
            created = user.get('created_at', '')[:10]
            email = user.get('email', '')[:30]
            print(f"{username:<20} {email:<30} {admin_str:<8} {active_str:<8} {created}")
        return 0
    
    elif args.user_action == 'delete':
        username = args.username or input("Username to delete: ")
        if user_manager.deactivate_user(username):
            print(f"User '{username}' deactivated.")
            return 0
        else:
            print(f"User '{username}' not found.")
            return 1
    
    elif args.user_action == 'token':
        username = args.username or input("Username: ")
        if username not in user_manager.users:
            print(f"User '{username}' not found.")
            return 1
        
        name = args.token_name or f"CLI token for {username}"
        expires_days = args.expires_days
        
        token = user_manager.create_token(username, name, expires_days)
        print(f"Token created for '{username}': {token}")
        print("Save this token securely - it won't be shown again.")
        return 0

def cmd_stats(args):
    """Show server statistics"""
    config = Config()
    package_manager = PackageManager(config.data_dir)
    
    packages = package_manager.get_all_packages()
    stats = package_manager.get_package_stats()
    
    print("📊 PyPI Clone Statistics")
    print("=" * 30)
    print(f"Packages: {stats['total_packages']}")
    print(f"Files: {stats['total_files']}")
    print(f"Total size: {stats['total_size_mb']} MB")
    print(f"Data directory: {config.data_dir}")
    
    if packages:
        print("\n📦 Recent packages:")
        # Show 5 most recent packages
        all_files = []
        for name, versions in packages.items():
            for version in versions:
                all_files.append((name, version))
        
        all_files.sort(key=lambda x: x[1].get('upload_time', ''), reverse=True)
        
        for name, file_info in all_files[:5]:
            version = file_info.get('version', 'unknown')
            upload_time = file_info.get('upload_time', '')
            if hasattr(upload_time, 'strftime'):
                upload_time = upload_time.strftime('%Y-%m-%d %H:%M')
            print(f"  • {name} {version} ({upload_time})")
    
    return 0

def cmd_packages(args):
    """Package management commands"""
    config = Config()
    package_manager = PackageManager(config.data_dir)
    
    if args.package_action == 'list':
        packages = package_manager.get_all_packages()
        
        if not packages:
            print("No packages found.")
            return 0
        
        print(f"{'Package':<30} {'Version':<15} {'Files':<8} {'Size (KB)':<12} {'Uploaded'}")
        print("-" * 85)
        
        for name, versions in packages.items():
            latest = versions[0] if versions else {}
            version = latest.get('version', 'unknown')
            size_kb = round(latest.get('size', 0) / 1024, 1)
            upload_time = latest.get('upload_time', '')
            if hasattr(upload_time, 'strftime'):
                upload_time = upload_time.strftime('%Y-%m-%d')
            
            print(f"{name:<30} {version:<15} {len(versions):<8} {size_kb:<12} {upload_time}")
        
        return 0
    
    elif args.package_action == 'search':
        query = args.query or input("Search query: ")
        results = package_manager.search_packages(query)
        
        if not results:
            print(f"No packages found matching '{query}'")
            return 0
        
        print(f"Found {len(results)} package(s) matching '{query}':")
        print()
        
        for pkg in results:
            print(f"📦 {pkg['name']} ({pkg['latest_version']})")
            if pkg['summary']:
                print(f"   {pkg['summary']}")
            if pkg['author']:
                print(f"   Author: {pkg['author']}")
            print()
        
        return 0
    
    elif args.package_action == 'info':
        package_name = args.package_name or input("Package name: ")
        packages = package_manager.get_all_packages()
        
        if package_name.lower() not in packages:
            print(f"Package '{package_name}' not found.")
            return 1
        
        versions = packages[package_name.lower()]
        latest = versions[0] if versions else {}
        
        print(f"📦 Package Information: {package_name}")
        print("=" * 50)
        print(f"Latest version: {latest.get('version', 'unknown')}")
        print(f"Summary: {latest.get('summary', 'No description')}")
        print(f"Author: {latest.get('author', 'Unknown')}")
        print(f"Home page: {latest.get('home_page', 'Not specified')}")
        print(f"Total versions: {len(versions)}")
        
        print("\n📁 Available files:")
        for version in versions:
            filename = version.get('filename', 'unknown')
            size_kb = round(version.get('size', 0) / 1024, 1)
            upload_time = version.get('upload_time', '')
            if hasattr(upload_time, 'strftime'):
                upload_time = upload_time.strftime('%Y-%m-%d %H:%M')
            print(f"  • {filename} ({size_kb} KB, {upload_time})")
        
        return 0

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="PyPI Clone server management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Start server command
    start_parser = subparsers.add_parser('start', help='Start the PyPI server')
    start_parser.add_argument('--host', help='Host to bind to')
    start_parser.add_argument('--port', type=int, help='Port to bind to')
    start_parser.add_argument('--data-dir', help='Directory to store packages')
    start_parser.add_argument('--auth', action='store_true', help='Enable authentication')
    start_parser.add_argument('--debug', action='store_true', help='Enable debug mode')
    start_parser.set_defaults(func=cmd_start)
    
    # Initialize command
    init_parser = subparsers.add_parser('init', help='Initialize configuration')
    init_parser.add_argument('--config', help='Configuration file path')
    init_parser.add_argument('--force', action='store_true', help='Overwrite existing config')
    init_parser.set_defaults(func=cmd_init)
    
    # User management
    user_parser = subparsers.add_parser('user', help='User management')
    user_subparsers = user_parser.add_subparsers(dest='user_action', help='User actions')
    
    # Create user
    create_user_parser = user_subparsers.add_parser('create', help='Create a new user')
    create_user_parser.add_argument('--username', help='Username')
    create_user_parser.add_argument('--password', help='Password')
    create_user_parser.add_argument('--email', help='Email address')
    create_user_parser.add_argument('--admin', action='store_true', help='Make user admin')
    create_user_parser.add_argument('--user-file', help='User database file')
    
    # List users
    list_users_parser = user_subparsers.add_parser('list', help='List all users')
    list_users_parser.add_argument('--user-file', help='User database file')
    
    # Delete user
    delete_user_parser = user_subparsers.add_parser('delete', help='Delete a user')
    delete_user_parser.add_argument('--username', help='Username to delete')
    delete_user_parser.add_argument('--user-file', help='User database file')
    
    # Create token
    token_parser = user_subparsers.add_parser('token', help='Create API token')
    token_parser.add_argument('--username', help='Username')
    token_parser.add_argument('--token-name', help='Token name')
    token_parser.add_argument('--expires-days', type=int, help='Token expiration in days')
    token_parser.add_argument('--user-file', help='User database file')
    
    user_parser.set_defaults(func=cmd_user)
    
    # Statistics
    stats_parser = subparsers.add_parser('stats', help='Show server statistics')
    stats_parser.set_defaults(func=cmd_stats)
    
    # Package management
    packages_parser = subparsers.add_parser('packages', help='Package management')
    packages_subparsers = packages_parser.add_subparsers(dest='package_action', help='Package actions')
    
    # List packages
    list_packages_parser = packages_subparsers.add_parser('list', help='List all packages')
    
    # Search packages
    search_packages_parser = packages_subparsers.add_parser('search', help='Search packages')
    search_packages_parser.add_argument('--query', help='Search query')
    
    # Package info
    info_packages_parser = packages_subparsers.add_parser('info', help='Show package information')
    info_packages_parser.add_argument('--package-name', help='Package name')
    
    packages_parser.set_defaults(func=cmd_packages)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)

if __name__ == '__main__':
    sys.exit(main())
