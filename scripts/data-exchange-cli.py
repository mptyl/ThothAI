#!/usr/bin/env python3
# Copyright (c) 2025 Tyl Consulting di Pancotti Marco
# This file is part of Thoth and is released under the MIT License.
# See the LICENSE.md file in the project root for full license information.

"""
CLI helper for data exchange operations.
Allows file upload/download without accessing the host filesystem.
Works with local development, docker-compose, and Docker Swarm deployments.
"""

import argparse
import requests
import os
import sys
from pathlib import Path

# Configuration - can be overridden via environment
DEFAULT_API_BASE = os.getenv('THOTH_API_BASE', 'http://localhost:8040')
DEFAULT_API_KEY = os.getenv('THOTH_API_KEY', '')


def list_files(base_url, api_key):
    """List all files in data_exchange"""
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    response = requests.get(f'{base_url}/api/data-exchange/list/', headers=headers)
    response.raise_for_status()

    data = response.json()
    files = data.get('files', [])

    if not files:
        print("No files found in data_exchange")
        return

    print(f"\n{'Filename':<40} {'Size (bytes)':<15} {'Modified'}")
    print("-" * 70)
    for f in files:
        print(f"{f['name']:<40} {f['size']:<15} {f['modified']}")


def upload_file(base_url, api_key, file_path):
    """Upload a file to data_exchange"""
    if not os.path.exists(file_path):
        print(f"Error: File '{file_path}' not found")
        sys.exit(1)

    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    filename = os.path.basename(file_path)

    with open(file_path, 'rb') as f:
        files = {'file': (filename, f)}
        response = requests.post(
            f'{base_url}/api/data-exchange/upload/',
            headers=headers,
            files=files
        )

    response.raise_for_status()
    print(f"Successfully uploaded: {filename}")


def download_file(base_url, api_key, filename, output_path=None):
    """Download a file from data_exchange"""
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    response = requests.get(
        f'{base_url}/api/data-exchange/download/{filename}/',
        headers=headers,
        stream=True
    )
    response.raise_for_status()

    if output_path is None:
        output_path = filename

    with open(output_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)

    print(f"Successfully downloaded to: {output_path}")


def delete_file(base_url, api_key, filename):
    """Delete a file from data_exchange"""
    headers = {}
    if api_key:
        headers['Authorization'] = f'Bearer {api_key}'

    response = requests.delete(
        f'{base_url}/api/data-exchange/delete/{filename}/',
        headers=headers
    )
    response.raise_for_status()

    print(f"Successfully deleted: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Thoth Data Exchange CLI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all files
  python data-exchange-cli.py list

  # Upload a file
  python data-exchange-cli.py upload my_data.csv

  # Download a file
  python data-exchange-cli.py download export.csv

  # Delete a file
  python data-exchange-cli.py delete old_data.csv

Environment Variables:
  THOTH_API_BASE    API base URL (default: http://localhost:8040)
  THOTH_API_KEY     API key for authentication (optional)
        """
    )

    parser.add_argument('--base-url', default=DEFAULT_API_BASE,
                        help='API base URL (default: from THOTH_API_BASE or http://localhost:8040)')
    parser.add_argument('--api-key', default=DEFAULT_API_KEY,
                        help='API key (default: from THOTH_API_KEY)')

    subparsers = parser.add_subparsers(dest='command', required=True)

    # List command
    subparsers.add_parser('list', help='List all files in data_exchange')

    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload a file')
    upload_parser.add_argument('file', help='Path to file to upload')

    # Download command
    download_parser = subparsers.add_parser('download', help='Download a file')
    download_parser.add_argument('filename', help='Name of file to download')
    download_parser.add_argument('-o', '--output', help='Output path (default: same as filename)')

    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete a file')
    delete_parser.add_argument('filename', help='Name of file to delete')

    args = parser.parse_args()

    try:
        if args.command == 'list':
            list_files(args.base_url, args.api_key)
        elif args.command == 'upload':
            upload_file(args.base_url, args.api_key, args.file)
        elif args.command == 'download':
            download_file(args.base_url, args.api_key, args.filename, args.output)
        elif args.command == 'delete':
            delete_file(args.base_url, args.api_key, args.filename)
    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
