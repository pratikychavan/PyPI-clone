#!/usr/bin/env python3
"""
Test script to verify PyPI Clone functionality
"""

import os
import sys
import json
import tempfile
import zipfile
import tarfile
from pathlib import Path
import requests
import subprocess

def create_test_package():
    """Create a simple test package for uploading"""
    temp_dir = Path(tempfile.mkdtemp())
    package_dir = temp_dir / "test_package"
    package_dir.mkdir()
    
    # Create setup.py
    setup_py = package_dir / "setup.py"
    setup_py.write_text("""
from setuptools import setup

setup(
    name="test-package",
    version="1.0.0",
    description="A test package for PyPI Clone",
    author="Test Author",
    author_email="test@example.com",
    packages=["test_package"],
    python_requires=">=3.6",
)
""")
    
    # Create package directory
    pkg_dir = package_dir / "test_package"
    pkg_dir.mkdir()
    
    # Create __init__.py
    init_py = pkg_dir / "__init__.py"
    init_py.write_text("""
__version__ = "1.0.0"

def hello():
    return "Hello from test package!"
""")
    
    # Create PKG-INFO for sdist
    pkg_info = package_dir / "PKG-INFO"
    pkg_info.write_text("""
Name: test-package
Version: 1.0.0
Summary: A test package for PyPI Clone
Author: Test Author
Author-email: test@example.com
""")
    
    # Create simple sdist
    sdist_path = temp_dir / "test-package-1.0.0.tar.gz"
    with tarfile.open(sdist_path, 'w:gz') as tar:
        tar.add(package_dir, arcname="test-package-1.0.0")
    
    return str(sdist_path)

def test_server_basic(base_url):
    """Test basic server functionality"""
    print("🧪 Testing basic server functionality...")
    
    # Test homepage
    try:
        response = requests.get(base_url)
        assert response.status_code == 200, f"Homepage failed: {response.status_code}"
        print("✅ Homepage accessible")
    except Exception as e:
        print(f"❌ Homepage test failed: {e}")
        return False
    
    # Test simple index
    try:
        response = requests.get(f"{base_url}/simple/")
        assert response.status_code == 200, f"Simple index failed: {response.status_code}"
        print("✅ Simple index accessible")
    except Exception as e:
        print(f"❌ Simple index test failed: {e}")
        return False
    
    # Test API stats
    try:
        response = requests.get(f"{base_url}/api/stats")
        assert response.status_code == 200, f"API stats failed: {response.status_code}"
        stats = response.json()
        assert isinstance(stats, dict), "Stats should be a dictionary"
        print("✅ API stats working")
    except Exception as e:
        print(f"❌ API stats test failed: {e}")
        return False
    
    return True

def test_package_upload(base_url, package_path, username=None, password=None):
    """Test package upload functionality"""
    print("🧪 Testing package upload...")
    
    try:
        with open(package_path, 'rb') as f:
            files = {'content': f}
            
            # Prepare auth if needed
            auth = None
            if username and password:
                auth = (username, password)
            
            response = requests.post(f"{base_url}/upload", files=files, auth=auth)
            
            if response.status_code == 200:
                print("✅ Package upload successful")
                result = response.json()
                print(f"   Uploaded: {result.get('filename')}")
                return True
            elif response.status_code == 401:
                print("⚠️  Package upload requires authentication")
                return False
            else:
                print(f"❌ Package upload failed: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"❌ Package upload test failed: {e}")
        return False

def test_package_download(base_url, filename):
    """Test package download functionality"""
    print("🧪 Testing package download...")
    
    try:
        response = requests.get(f"{base_url}/packages/{filename}")
        
        if response.status_code == 200:
            print("✅ Package download successful")
            print(f"   Downloaded {len(response.content)} bytes")
            return True
        elif response.status_code == 404:
            print("⚠️  Package not found (may not have been uploaded)")
            return False
        else:
            print(f"❌ Package download failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Package download test failed: {e}")
        return False

def test_search(base_url):
    """Test package search functionality"""
    print("🧪 Testing package search...")
    
    try:
        response = requests.get(f"{base_url}/search?q=test")
        
        if response.status_code == 200:
            results = response.json()
            assert isinstance(results, dict), "Search results should be a dictionary"
            assert 'packages' in results, "Search results should contain 'packages' key"
            print("✅ Package search working")
            if results['packages']:
                print(f"   Found {len(results['packages'])} package(s)")
            return True
        else:
            print(f"❌ Package search failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Package search test failed: {e}")
        return False

def test_pip_compatibility(base_url):
    """Test pip compatibility"""
    print("🧪 Testing pip compatibility...")
    
    try:
        # Test simple index format
        response = requests.get(f"{base_url}/simple/")
        if response.status_code != 200:
            print(f"❌ Simple index not accessible: {response.status_code}")
            return False
        
        content = response.text
        if '<a href=' not in content and 'Simple index' in content:
            print("✅ Simple index format looks correct")
            return True
        else:
            print("⚠️  Simple index format may not be pip-compatible")
            return False
            
    except Exception as e:
        print(f"❌ Pip compatibility test failed: {e}")
        return False

def run_tests(base_url="http://localhost:8080", username=None, password=None):
    """Run all tests"""
    print("🚀 Starting PyPI Clone tests...")
    print(f"📍 Testing server at: {base_url}")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 0
    
    # Test basic functionality
    total_tests += 1
    if test_server_basic(base_url):
        tests_passed += 1
    
    # Create test package
    print("\n📦 Creating test package...")
    package_path = create_test_package()
    package_filename = Path(package_path).name
    print(f"   Created: {package_filename}")
    
    # Test package upload
    total_tests += 1
    upload_success = test_package_upload(base_url, package_path, username, password)
    if upload_success:
        tests_passed += 1
    
    # Test package download (only if upload succeeded)
    if upload_success:
        total_tests += 1
        if test_package_download(base_url, package_filename):
            tests_passed += 1
    
    # Test search
    total_tests += 1
    if test_search(base_url):
        tests_passed += 1
    
    # Test pip compatibility
    total_tests += 1
    if test_pip_compatibility(base_url):
        tests_passed += 1
    
    # Clean up
    try:
        os.unlink(package_path)
        os.rmdir(Path(package_path).parent)
    except:
        pass
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! PyPI Clone is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

def main():
    """Main test runner"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test PyPI Clone server")
    parser.add_argument('--url', default='http://localhost:8080', 
                       help='Base URL of PyPI server (default: http://localhost:8080)')
    parser.add_argument('--username', help='Username for authentication')
    parser.add_argument('--password', help='Password for authentication')
    
    args = parser.parse_args()
    
    success = run_tests(args.url, args.username, args.password)
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
