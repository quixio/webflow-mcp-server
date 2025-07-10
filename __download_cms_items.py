#!/usr/bin/env python3
"""
Download all CMS items from the Webflow Glossary collection and save them as JSON files.
This allows for local editing and re-uploading of items without creating duplicates.
"""

import os
import json
import requests
from pathlib import Path
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBFLOW_TOKEN = os.getenv('WEBFLOW_TOKEN')
SITE_ID = '64872dd3805a32626f4c2952'
COLLECTION_ID = '685d76e77ec5b27b52412675'
BASE_URL = 'https://api.webflow.com/v2'
OUTPUT_DIR = 'cms_items'

class WebflowDownloader:
    def __init__(self):
        self.headers = {
            'Authorization': f'Bearer {WEBFLOW_TOKEN}',
            'Content-Type': 'application/json'
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def get_all_cms_items(self) -> List[Dict[str, Any]]:
        """Fetch all CMS items from the collection using pagination."""
        all_items = []
        offset = 0
        limit = 100  # Maximum allowed per request
        
        print(f"Fetching CMS items from collection {COLLECTION_ID}...")
        
        while True:
            print(f"  Fetching items {offset}-{offset + limit}...")
            
            # Make API request
            url = f'{BASE_URL}/collections/{COLLECTION_ID}/items'
            params = {
                'limit': limit,
                'offset': offset
            }
            
            try:
                response = self.session.get(url, params=params)
                
                if response.status_code != 200:
                    print(f"✗ Error fetching items: HTTP {response.status_code}")
                    print(f"Response: {response.text}")
                    break
                
                data = response.json()
                items = data.get('items', [])
                
                if not items:
                    print("  No more items found.")
                    break
                
                all_items.extend(items)
                print(f"  Retrieved {len(items)} items")
                
                # Check if we've reached the end
                pagination = data.get('pagination', {})
                total = pagination.get('total', 0)
                
                if len(all_items) >= total:
                    print(f"  Reached end - total items: {total}")
                    break
                
                offset += limit
                
            except Exception as e:
                print(f"✗ Error fetching items: {e}")
                break
        
        print(f"✓ Fetched {len(all_items)} total items")
        return all_items
    
    def sanitize_filename(self, name: str) -> str:
        """Convert item name to a safe filename."""
        # Remove/replace characters that aren't safe for filenames
        safe_name = name.replace('/', '-').replace('\\', '-').replace(':', '-')
        safe_name = safe_name.replace('?', '').replace('*', '').replace('<', '').replace('>', '')
        safe_name = safe_name.replace('|', '-').replace('"', '').replace('\n', ' ').replace('\r', ' ')
        # Limit length and clean up spaces
        safe_name = safe_name.strip()[:100]  # Limit to 100 characters
        return safe_name
    
    def save_items_as_json(self, items: List[Dict[str, Any]]) -> None:
        """Save each CMS item as a separate JSON file."""
        # Create output directory
        output_path = Path(OUTPUT_DIR)
        output_path.mkdir(exist_ok=True)
        
        print(f"\nSaving items to {OUTPUT_DIR}/ directory...")
        
        # Also create a summary file with all item metadata
        summary_data = {
            'collection_id': COLLECTION_ID,
            'site_id': SITE_ID,
            'download_timestamp': str(datetime.utcnow()) if 'datetime' in globals() else 'unknown',
            'total_items': len(items),
            'items': []
        }
        
        for item in items:
            item_id = item.get('id', 'unknown_id')
            item_name = item.get('fieldData', {}).get('name', 'Untitled')
            item_slug = item.get('fieldData', {}).get('slug', item_id)
            
            # Create safe filename using slug (preferred) or sanitized name
            filename = self.sanitize_filename(item_slug) if item_slug else self.sanitize_filename(item_name)
            filename = f"{filename}_{item_id}.json"
            
            # Save individual item file
            file_path = output_path / filename
            
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(item, f, indent=2, ensure_ascii=False)
                
                print(f"  ✓ Saved: {filename}")
                
                # Add to summary
                summary_data['items'].append({
                    'id': item_id,
                    'name': item_name,
                    'slug': item_slug,
                    'filename': filename,
                    'created_on': item.get('createdOn'),
                    'last_updated': item.get('lastUpdated'),
                    'is_draft': item.get('isDraft', False),
                    'is_archived': item.get('isArchived', False)
                })
                
            except Exception as e:
                print(f"  ✗ Error saving {filename}: {e}")
        
        # Save summary file
        summary_path = output_path / '_summary.json'
        try:
            with open(summary_path, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            print(f"\n✓ Saved summary file: {summary_path}")
        except Exception as e:
            print(f"✗ Error saving summary file: {e}")
    
    def create_upload_script(self) -> None:
        """Create a companion script for uploading modified items back to Webflow."""
        upload_script = '''#!/usr/bin/env python3
"""
Upload modified CMS items back to Webflow.
This script updates existing items rather than creating new ones.
"""

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

WEBFLOW_TOKEN = os.getenv('WEBFLOW_TOKEN')
COLLECTION_ID = '685d76e77ec5b27b52412675'
BASE_URL = 'https://api.webflow.com/v2'
CMS_ITEMS_DIR = 'cms_items'

def upload_item(item_data):
    """Upload a single item back to Webflow."""
    headers = {
        'Authorization': f'Bearer {WEBFLOW_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    item_id = item_data.get('id')
    if not item_id:
        print("✗ Item has no ID, cannot update")
        return False
    
    # Prepare update payload - only include fieldData
    update_data = {
        "items": [{
            "id": item_id,
            "fieldData": item_data.get('fieldData', {})
        }]
    }
    
    try:
        response = requests.put(
            f'{BASE_URL}/collections/{COLLECTION_ID}/items',
            headers=headers,
            json=update_data
        )
        
        if response.status_code in [200, 202]:
            print(f"✓ Updated item: {item_data.get('fieldData', {}).get('name', item_id)}")
            return True
        else:
            print(f"✗ Failed to update item {item_id}: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"✗ Error updating item {item_id}: {e}")
        return False

def main():
    """Upload all JSON files in the cms_items directory."""
    cms_dir = Path(CMS_ITEMS_DIR)
    
    if not cms_dir.exists():
        print(f"✗ Directory {CMS_ITEMS_DIR} not found")
        return
    
    # Get all JSON files except summary
    json_files = [f for f in cms_dir.glob('*.json') if not f.name.startswith('_')]
    
    if not json_files:
        print(f"✗ No JSON files found in {CMS_ITEMS_DIR}")
        return
    
    print(f"Found {len(json_files)} items to upload...")
    
    successful = 0
    failed = 0
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                item_data = json.load(f)
            
            if upload_item(item_data):
                successful += 1
            else:
                failed += 1
                
        except Exception as e:
            print(f"✗ Error reading {json_file}: {e}")
            failed += 1
    
    print(f"\\n=== Upload Summary ===")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(json_files)}")

if __name__ == "__main__":
    main()
'''
        
        upload_script_path = Path('upload_cms_items.py')
        try:
            with open(upload_script_path, 'w', encoding='utf-8') as f:
                f.write(upload_script)
            print(f"✓ Created upload script: {upload_script_path}")
            print("  Use this script to upload your modified JSON files back to Webflow")
        except Exception as e:
            print(f"✗ Error creating upload script: {e}")

def main():
    if not WEBFLOW_TOKEN:
        print("✗ WEBFLOW_TOKEN not found in environment")
        return
    
    print("=== Webflow CMS Items Downloader ===")
    print(f"Site ID: {SITE_ID}")
    print(f"Collection ID: {COLLECTION_ID}")
    print(f"Output Directory: {OUTPUT_DIR}")
    print()
    
    downloader = WebflowDownloader()
    
    # Download all items
    items = downloader.get_all_cms_items()
    
    if not items:
        print("✗ No items found to download")
        return
    
    # Save items as JSON files
    downloader.save_items_as_json(items)
    
    # Create upload script
    downloader.create_upload_script()
    
    print(f"\n=== Download Complete ===")
    print(f"Downloaded: {len(items)} items")
    print(f"Saved to: {OUTPUT_DIR}/")
    print("\nTo edit and re-upload:")
    print("1. Edit the JSON files in the cms_items/ directory")
    print("2. Run: python3 upload_cms_items.py")
    print("\nNote: Only modify the 'fieldData' section in each JSON file")

if __name__ == "__main__":
    # Import datetime for summary
    from datetime import datetime
    main()