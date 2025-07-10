#!/usr/bin/env python3
"""
Batch upload markdown files to Webflow CMS.
Processes markdown files with images and uploads them to the Glossaries collection.
"""

import os
import re
import hashlib
import requests
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
WEBFLOW_TOKEN = os.getenv('WEBFLOW_TOKEN')
SITE_ID = '64872dd3805a32626f4c2952'
COLLECTION_ID = '685d76e77ec5b27b52412675'
BASE_URL = 'https://api.webflow.com/v2'

class WebflowUploader:
    def __init__(self):
        self.headers = {
            'Authorization': f'Bearer {WEBFLOW_TOKEN}',
            'Content-Type': 'application/json'
        }
        self.uploaded_images = {}  # Cache for uploaded images
    
    def get_file_md5(self, file_path: str) -> str:
        """Calculate MD5 hash of a file."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def upload_image(self, image_path: str, display_name: str) -> Optional[str]:
        """Upload an image to Webflow and return the hosted URL."""
        if image_path in self.uploaded_images:
            return self.uploaded_images[image_path]
        
        try:
            file_hash = self.get_file_md5(image_path)
            file_name = os.path.basename(image_path)
            
            # Create asset in Webflow
            asset_data = {
                'fileName': file_name,
                'fileHash': file_hash,
                'displayName': display_name
            }
            
            response = requests.post(
                f'{BASE_URL}/sites/{SITE_ID}/assets',
                headers=self.headers,
                json=asset_data
            )
            
            if response.status_code in [200, 202]:
                result = response.json()
                print(f"✓ Asset creation response: {result}")
                
                # Check for both hostedUrl and url fields
                hosted_url = result.get('hostedUrl') or result.get('url')
                
                # If we got an uploadUrl, we need to upload the file
                if 'uploadUrl' in result:
                    upload_url = result['uploadUrl']
                    upload_data = result.get('uploadDetails', {})
                    
                    # Upload the actual file
                    with open(image_path, 'rb') as f:
                        files = {'file': (file_name, f, 'image/png')}
                        upload_response = requests.post(upload_url, files=files, data=upload_data)
                        
                        if upload_response.status_code in [200, 201, 204]:
                            # Get the final hosted URL - might be in the original response
                            hosted_url = result.get('hostedUrl') or f"https://cdn.prod.website-files.com/{SITE_ID}/{result.get('id', '')}"
                            print(f"✓ File uploaded successfully: {file_name}")
                        else:
                            print(f"✗ Failed to upload file data: HTTP {upload_response.status_code}")
                            return None
                
                if hosted_url:
                    self.uploaded_images[image_path] = hosted_url
                    print(f"✓ Uploaded image: {file_name} -> {hosted_url}")
                    return hosted_url
                else:
                    print(f"✗ No hosted URL in response for {file_name}")
                    print(f"Response: {result}")
                    return None
            else:
                print(f"✗ Failed to upload {file_name}: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"✗ Error uploading {image_path}: {e}")
            return None
    
    def parse_markdown_file(self, file_path: str) -> Dict[str, str]:
        """Parse a markdown file and extract components."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract title (first # heading)
        title_match = re.search(r'^# (.+)$', content, re.MULTILINE)
        title = title_match.group(1) if title_match else "Untitled"
        
        # Create slug
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        
        # Extract summary from ??? info "Summary" or ???+ info "Summary" block
        summary_pattern = r'\?\?\?\+? info "Summary"\s*\n((?:    .+\n?)+)'
        summary_match = re.search(summary_pattern, content, re.MULTILINE)
        summary = ""
        if summary_match:
            summary_lines = summary_match.group(1).split('\n')
            summary = ' '.join(line.strip() for line in summary_lines if line.strip())
        
        # Get content after summary block
        if summary_match:
            body_start = summary_match.end()
            body_content = content[body_start:].strip()
        else:
            # If no summary, get everything after the title
            if title_match:
                body_start = title_match.end()
                body_content = content[body_start:].strip()
            else:
                body_content = content
        
        return {
            'title': title,
            'slug': slug,
            'summary': summary,
            'body': body_content
        }
    
    def convert_cross_references(self, text: str) -> str:
        """Convert markdown cross-references to absolute URLs."""
        # Pattern for [text](file.md) links
        pattern = r'\[([^\]]+)\]\(([^)]+\.md)\)'
        
        def replace_link(match):
            link_text = match.group(1)
            file_name = match.group(2)
            # Convert filename to slug (remove .md, lowercase, hyphens)
            slug = re.sub(r'[^a-z0-9]+', '-', file_name.replace('.md', '').lower()).strip('-')
            return f'<a href="https://quix.io/glossary/{slug}" id="">{link_text}</a>'
        
        # First convert .md file references
        text = re.sub(pattern, replace_link, text)
        
        # Then convert [text](https://url) links to proper HTML
        url_pattern = r'\[([^\]]+)\]\((https?://[^)]+)\)'
        
        def replace_url_link(match):
            link_text = match.group(1)
            url = match.group(2)
            return f'<a href="{url}" id="">{link_text}</a>'
        
        text = re.sub(url_pattern, replace_url_link, text)
        
        return text
    
    def markdown_to_html(self, markdown_text: str, images_dir: str) -> str:
        """Convert markdown to HTML with proper formatting."""
        html = markdown_text
        
        # Convert cross-references first
        html = self.convert_cross_references(html)
        
        # Handle images
        image_pattern = r'!\[([^\]]*)\]\(images/([^)]+)\)'
        
        def replace_image(match):
            alt_text = match.group(1)
            image_file = match.group(2)
            image_path = os.path.join(images_dir, image_file)
            
            if os.path.exists(image_path):
                display_name = image_file.replace('_', ' ').replace('.png', '').title()
                hosted_url = self.upload_image(image_path, display_name)
                
                if hosted_url:
                    return f'''<figure id="" class="w-richtext-figure-type-image w-richtext-align-fullwidth" style="max-width:1600px" data-rt-type="image" data-rt-align="fullwidth" data-rt-max-width="1600px"><div id=""><img src="{hosted_url}" width="auto" height="auto" alt="{alt_text}" loading="auto" id=""></div></figure>'''
                else:
                    return f'<p id="">[Image: {image_file} - Upload failed]</p>'
            else:
                return f'<p id="">[Image: {image_file} - File not found]</p>'
        
        html = re.sub(image_pattern, replace_image, html)
        
        # Process line by line to handle different content types
        lines = html.split('\n')
        result_lines = []
        current_list_items = []
        in_code_block = False
        code_block_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # Skip empty lines when not in code block
            if not stripped and not in_code_block:
                i += 1
                continue
                
            # Handle code block fences
            if stripped.startswith('```'):
                if not in_code_block:
                    # Starting a code block
                    in_code_block = True
                    code_block_lines = [line]
                else:
                    # Ending a code block
                    in_code_block = False
                    code_block_lines.append(line)
                    # Close any open list before adding code block
                    if current_list_items:
                        list_html = '<ol id="">' + ''.join(current_list_items) + '</ol>'
                        result_lines.append(list_html)
                        current_list_items = []
                    # Add the entire code block as a paragraph
                    code_content = '\n'.join(code_block_lines)
                    result_lines.append(f'<p id="">{code_content}</p>')
                    code_block_lines = []
                i += 1
                continue
            
            # If we're inside a code block, collect lines without processing
            if in_code_block:
                code_block_lines.append(line)
                i += 1
                continue
                
            # Handle headers (only when not in code block)
            if stripped.startswith('### '):
                # Close any open list
                if current_list_items:
                    list_html = '<ol id="">' + ''.join(current_list_items) + '</ol>'
                    result_lines.append(list_html)
                    current_list_items = []
                content = stripped[4:].strip()
                result_lines.append(f'<h3 id="">{content}</h3>')
            elif stripped.startswith('## '):
                # Close any open list
                if current_list_items:
                    list_html = '<ol id="">' + ''.join(current_list_items) + '</ol>'
                    result_lines.append(list_html)
                    current_list_items = []
                content = stripped[3:].strip()
                result_lines.append(f'<h2 id="">{content}</h2>')
            elif stripped.startswith('# '):
                # Close any open list
                if current_list_items:
                    list_html = '<ol id="">' + ''.join(current_list_items) + '</ol>'
                    result_lines.append(list_html)
                    current_list_items = []
                content = stripped[2:].strip()
                result_lines.append(f'<h1 id="">{content}</h1>')
            # Handle numbered lists
            elif re.match(r'^\d+\.\s+', stripped):
                content = re.sub(r'^\d+\.\s+', '', stripped)
                # Convert bold text in list items
                content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', content)
                current_list_items.append(f'<li id="">{content}</li>')
            # Handle figure tags (already processed images)
            elif stripped.startswith('<figure'):
                # Close any open list
                if current_list_items:
                    list_html = '<ol id="">' + ''.join(current_list_items) + '</ol>'
                    result_lines.append(list_html)
                    current_list_items = []
                result_lines.append(stripped)
            # Handle regular paragraphs
            else:
                # Close any open list
                if current_list_items:
                    list_html = '<ol id="">' + ''.join(current_list_items) + '</ol>'
                    result_lines.append(list_html)
                    current_list_items = []
                # Convert bold text
                content = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', stripped)
                result_lines.append(f'<p id="">{content}</p>')
            
            i += 1
        
        # Close any open lists
        if current_list_items:
            list_html = '<ol id="">' + ''.join(current_list_items) + '</ol>'
            result_lines.append(list_html)
        
        # Handle case where code block wasn't closed
        if in_code_block and code_block_lines:
            code_content = '\n'.join(code_block_lines)
            result_lines.append(f'<p id="">{code_content}</p>')
        
        return '\n'.join(result_lines)
    
    def create_cms_item(self, data: Dict[str, str]) -> bool:
        """Create a CMS item in Webflow."""
        item_data = {
            "items": [{
                "fieldData": {
                    "name": data['title'],
                    "slug": data['slug'],
                    "summary-box": f'<p id="">{self.convert_cross_references(data["summary"])}</p>',
                    "body-text": data['body_html'],
                    "full-width": "31a4ccad471c61f1c9e32c9b034cc504"  # false option ID
                }
            }]
        }
        
        try:
            response = requests.post(
                f'{BASE_URL}/collections/{COLLECTION_ID}/items',
                headers=self.headers,
                json=item_data
            )
            
            if response.status_code in [200, 202]:
                result = response.json()
                if 'items' in result and len(result['items']) > 0:
                    print(f"✓ Created CMS item: {data['title']}")
                    return True
                else:
                    print(f"✗ Unexpected response format for {data['title']}")
                    print(f"Response: {response.text}")
                    return False
            else:
                print(f"✗ Failed to create CMS item for {data['title']}: HTTP {response.status_code}")
                print(f"Response: {response.text}")
                return False
                
        except Exception as e:
            print(f"✗ Error creating CMS item for {data['title']}: {e}")
            return False
    
    def process_directory(self, directory: str):
        """Process all markdown files in a directory."""
        directory = Path(directory)
        images_dir = directory / 'images'
        
        if not directory.exists():
            print(f"✗ Directory not found: {directory}")
            return
        
        if not images_dir.exists():
            print(f"⚠ Images directory not found: {images_dir}")
        
        # Find all markdown files
        md_files = list(directory.glob('*.md'))
        
        if not md_files:
            print(f"✗ No markdown files found in {directory}")
            return
        
        print(f"Found {len(md_files)} markdown files to process")
        
        successful = 0
        failed = 0
        
        for md_file in md_files:
            print(f"\nProcessing: {md_file.name}")
            
            try:
                # Parse markdown file
                parsed = self.parse_markdown_file(md_file)
                
                # Convert body to HTML
                parsed['body_html'] = self.markdown_to_html(parsed['body'], str(images_dir))
                
                # Create CMS item
                if self.create_cms_item(parsed):
                    successful += 1
                else:
                    failed += 1
                    
            except Exception as e:
                print(f"✗ Error processing {md_file.name}: {e}")
                failed += 1
        
        print(f"\n=== Summary ===")
        print(f"Successful: {successful}")
        print(f"Failed: {failed}")
        print(f"Total: {len(md_files)}")

def main():
    if not WEBFLOW_TOKEN:
        print("✗ WEBFLOW_TOKEN not found in environment")
        return
    
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python batch_upload.py <directory_path>")
        print("Example: python batch_upload.py input_batch2025_07_03")
        return
    
    directory = sys.argv[1]
    uploader = WebflowUploader()
    uploader.process_directory(directory)

if __name__ == "__main__":
    main()
