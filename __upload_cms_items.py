#!/usr/bin/env python3
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
        response = requests.patch(
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
    
    print(f"\n=== Upload Summary ===")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    print(f"Total: {len(json_files)}")

if __name__ == "__main__":
    main()
