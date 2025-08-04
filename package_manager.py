#!/usr/bin/env python3
"""
Package management utilities for PyPI Clone
"""

import os
import re
import json
import hashlib
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from packaging.utils import parse_wheel_filename, parse_sdist_filename
from packaging.version import parse as parse_version, InvalidVersion

class PackageManager:
    """Manages packages in the PyPI server"""
    
    def __init__(self, data_dir):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_cache = {}
    
    def get_all_packages(self):
        """Get information about all packages"""
        packages = {}
        
        for file_path in self.data_dir.rglob('*'):
            if not file_path.is_file():
                continue
                
            if not (file_path.suffix == '.whl' or file_path.name.endswith('.tar.gz')):
                continue
            
            try:
                package_info = self.get_package_info(file_path)
                if package_info:
                    name = package_info['name'].lower()
                    if name not in packages:
                        packages[name] = []
                    packages[name].append(package_info)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
        
        # Sort versions for each package
        for name in packages:
            packages[name].sort(key=lambda x: self._version_key(x.get('version', '0.0.0')), reverse=True)
        
        return packages
    
    def get_package_info(self, file_path):
        """Get information about a single package file"""
        file_path = Path(file_path)
        
        if not file_path.exists():
            return None
        
        # Check cache first
        cache_key = f"{file_path}:{file_path.stat().st_mtime}"
        if cache_key in self.metadata_cache:
            return self.metadata_cache[cache_key]
        
        filename = file_path.name
        stat = file_path.stat()
        
        package_info = {
            'filename': filename,
            'path': str(file_path.relative_to(self.data_dir)),
            'size': stat.st_size,
            'upload_time': datetime.fromtimestamp(stat.st_mtime),
            'md5_digest': self._calculate_hash(file_path, 'md5'),
            'sha256_digest': self._calculate_hash(file_path, 'sha256')
        }
        
        # Extract metadata
        try:
            if filename.endswith('.whl'):
                metadata = self._extract_wheel_metadata(file_path)
                # Parse wheel filename for name and version
                try:
                    name, version, build_tag, python_tag, abi_tag, platform_tag = parse_wheel_filename(filename)
                    metadata.update({
                        'name': name,
                        'version': str(version),
                        'python_tag': python_tag,
                        'abi_tag': abi_tag,
                        'platform_tag': platform_tag,
                        'build_tag': build_tag
                    })
                except Exception:
                    pass
            elif filename.endswith('.tar.gz'):
                metadata = self._extract_sdist_metadata(file_path)
                # Try to parse sdist filename
                try:
                    name, version = parse_sdist_filename(filename)
                    metadata.update({
                        'name': name,
                        'version': str(version)
                    })
                except Exception:
                    # Fallback to simple parsing
                    base_name = filename.replace('.tar.gz', '')
                    parts = base_name.split('-')
                    if len(parts) >= 2:
                        name = '-'.join(parts[:-1])
                        version = parts[-1]
                        metadata.update({
                            'name': name,
                            'version': version
                        })
            
            package_info.update(metadata)
        except Exception as e:
            print(f"Error extracting metadata from {filename}: {e}")
        
        # Cache the result
        self.metadata_cache[cache_key] = package_info
        return package_info
    
    def _extract_wheel_metadata(self, file_path):
        """Extract metadata from wheel file"""
        metadata = {}
        try:
            with zipfile.ZipFile(file_path, 'r') as zf:
                # Find METADATA file
                metadata_file = None
                for name in zf.namelist():
                    if name.endswith('.dist-info/METADATA'):
                        metadata_file = name
                        break
                
                if metadata_file:
                    with zf.open(metadata_file) as f:
                        content = f.read().decode('utf-8')
                        metadata = self._parse_metadata(content)
        except Exception as e:
            print(f"Error reading wheel metadata: {e}")
        
        return metadata
    
    def _extract_sdist_metadata(self, file_path):
        """Extract metadata from source distribution"""
        metadata = {}
        try:
            with tarfile.open(file_path, 'r:gz') as tf:
                # Look for PKG-INFO file
                pkg_info_file = None
                for member in tf.getmembers():
                    if member.name.endswith('/PKG-INFO') or member.name == 'PKG-INFO':
                        pkg_info_file = member
                        break
                
                if pkg_info_file:
                    f = tf.extractfile(pkg_info_file)
                    if f:
                        content = f.read().decode('utf-8')
                        metadata = self._parse_metadata(content)
        except Exception as e:
            print(f"Error reading sdist metadata: {e}")
        
        return metadata
    
    def _parse_metadata(self, content):
        """Parse PKG-INFO/METADATA format"""
        metadata = {}
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if not line or not ':' in line:
                i += 1
                continue
            
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            
            # Handle multiline values
            if key in ['Description', 'Description-Content-Type']:
                description_lines = [value] if value else []
                i += 1
                while i < len(lines) and (lines[i].startswith('        ') or lines[i].strip() == ''):
                    description_lines.append(lines[i].rstrip())
                    i += 1
                metadata[key.lower().replace('-', '_')] = '\n'.join(description_lines).strip()
                continue
            
            metadata[key.lower().replace('-', '_')] = value
            i += 1
        
        return metadata
    
    def _calculate_hash(self, file_path, algorithm='md5'):
        """Calculate hash of file"""
        if algorithm == 'md5':
            hasher = hashlib.md5()
        elif algorithm == 'sha256':
            hasher = hashlib.sha256()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
        
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""
    
    def _version_key(self, version_string):
        """Create a sortable key from version string"""
        try:
            return parse_version(version_string)
        except InvalidVersion:
            # Fallback for invalid versions
            return parse_version("0.0.0")
    
    def store_package(self, file_data, filename, overwrite=False):
        """Store a package file"""
        filepath = self.data_dir / filename
        
        if filepath.exists() and not overwrite:
            raise FileExistsError(f"Package {filename} already exists")
        
        # Create directory if needed
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        with open(filepath, 'wb') as f:
            f.write(file_data)
        
        return filepath
    
    def delete_package(self, filename):
        """Delete a package file"""
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            raise FileNotFoundError(f"Package {filename} not found")
        
        filepath.unlink()
        
        # Clean up cache
        cache_keys_to_remove = [key for key in self.metadata_cache.keys() if filename in key]
        for key in cache_keys_to_remove:
            del self.metadata_cache[key]
    
    def search_packages(self, query):
        """Search packages by name or description"""
        query = query.lower()
        packages = self.get_all_packages()
        results = []
        
        for name, versions in packages.items():
            if query in name.lower():
                # Get latest version
                latest = versions[0] if versions else {}
                results.append({
                    'name': name,
                    'latest_version': latest.get('version', 'unknown'),
                    'summary': latest.get('summary', ''),
                    'description': latest.get('description', ''),
                    'author': latest.get('author', ''),
                    'home_page': latest.get('home_page', ''),
                    'versions': [v.get('version', 'unknown') for v in versions]
                })
            else:
                # Search in descriptions
                for version in versions:
                    summary = version.get('summary', '').lower()
                    description = version.get('description', '').lower()
                    if query in summary or query in description:
                        results.append({
                            'name': name,
                            'latest_version': version.get('version', 'unknown'),
                            'summary': version.get('summary', ''),
                            'description': version.get('description', ''),
                            'author': version.get('author', ''),
                            'home_page': version.get('home_page', ''),
                            'versions': [v.get('version', 'unknown') for v in versions]
                        })
                        break
        
        return results
    
    def get_package_stats(self):
        """Get statistics about packages"""
        packages = self.get_all_packages()
        
        total_packages = len(packages)
        total_files = sum(len(versions) for versions in packages.values())
        total_size = 0
        
        for versions in packages.values():
            for version in versions:
                total_size += version.get('size', 0)
        
        return {
            'total_packages': total_packages,
            'total_files': total_files,
            'total_size': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2)
        }
