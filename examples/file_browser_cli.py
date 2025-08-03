#!/usr/bin/env python3
"""
Example: Programmatic File Browser

This example demonstrates how to build a simple file browser
using the RunpodStorageAPI programmatically (not using the interactive CLI).
"""

import os
from pathlib import Path
from runpod_storage import RunpodStorageAPI


class FileBrowser:
    """Simple programmatic file browser for Runpod network volumes."""
    
    def __init__(self, api_key=None):
        self.api = RunpodStorageAPI(api_key=api_key)
        self.volume_id = None
        self.current_path = ""
    
    def select_volume(self):
        """Select a volume to browse."""
        volumes = self.api.list_volumes()
        if not volumes:
            print("❌ No volumes found.")
            return False
        
        print("📁 Available volumes:")
        for i, volume in enumerate(volumes):
            print(f"  {i+1}. {volume['id']} ({volume.get('name', 'Unnamed')})")
        
        try:
            choice = int(input("Select volume (number): ")) - 1
            self.volume_id = volumes[choice]['id']
            print(f"✅ Selected volume: {self.volume_id}")
            return True
        except (ValueError, IndexError):
            print("❌ Invalid selection.")
            return False
    
    def list_current_directory(self):
        """List files and directories in current path."""
        if not self.volume_id:
            print("❌ No volume selected.")
            return [], []
        
        try:
            files = self.api.list_files(self.volume_id, self.current_path)
        except Exception as e:
            print(f"❌ Error listing files: {e}")
            return [], []
        
        # Separate directories and files
        directories = set()
        file_list = []
        
        for file_info in files:
            key = file_info["key"]
            
            # Remove current path prefix
            if self.current_path:
                if not key.startswith(self.current_path):
                    continue
                relative_key = key[len(self.current_path):].lstrip('/')
            else:
                relative_key = key
            
            # Check if this is in a subdirectory
            if '/' in relative_key:
                dir_name = relative_key.split('/')[0]
                directories.add(dir_name)
            else:
                # This is a file in current directory
                file_list.append(file_info)
        
        return sorted(directories), file_list
    
    def display_current_directory(self):
        """Display current directory contents."""
        print(f"\n📂 Current path: /{self.current_path}")
        print("=" * 60)
        
        directories, files = self.list_current_directory()
        
        # Display directories
        if directories:
            print("📁 Directories:")
            for i, dir_name in enumerate(directories, 1):
                print(f"  {i:2d}. 📁 {dir_name}/")
        
        # Display files
        if files:
            print(f"\n📄 Files:")
            for i, file_info in enumerate(files, 1):
                key = file_info["key"]
                if self.current_path:
                    display_name = key[len(self.current_path):].lstrip('/')
                else:
                    display_name = key
                
                size = file_info["size"]
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024 * 1024:
                    size_str = f"{size / 1024:.1f} KB"
                elif size < 1024 * 1024 * 1024:
                    size_str = f"{size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{size / (1024 * 1024 * 1024):.1f} GB"
                
                modified = file_info["last_modified"].strftime("%Y-%m-%d %H:%M")
                print(f"  {i:2d}. 📄 {display_name:<30} {size_str:>10} {modified}")
        
        if not directories and not files:
            print("📭 Directory is empty.")
    
    def navigate_to_directory(self, dir_name):
        """Navigate to a subdirectory."""
        if self.current_path:
            new_path = f"{self.current_path}/{dir_name}"
        else:
            new_path = dir_name
        
        self.current_path = new_path
        print(f"📁 Navigated to: /{self.current_path}")
    
    def go_up_directory(self):
        """Go up one directory level."""
        if self.current_path:
            parts = self.current_path.split('/')
            if len(parts) > 1:
                self.current_path = '/'.join(parts[:-1])
            else:
                self.current_path = ""
            print(f"📁 Navigated to: /{self.current_path}")
        else:
            print("📁 Already at root directory.")
    
    def download_file(self, file_info):
        """Download a selected file."""
        remote_path = file_info["key"]
        local_name = Path(remote_path).name
        
        try:
            print(f"⬇️  Downloading {remote_path} to {local_name}...")
            self.api.download_file(self.volume_id, remote_path, local_name)
            print(f"✅ Downloaded: {local_name}")
        except Exception as e:
            print(f"❌ Download failed: {e}")
    
    def delete_file(self, file_info):
        """Delete a selected file."""
        remote_path = file_info["key"]
        
        confirm = input(f"🗑️  Delete {remote_path}? (y/N): ").strip().lower()
        if confirm == 'y':
            try:
                self.api.delete_file(self.volume_id, remote_path)
                print(f"✅ Deleted: {remote_path}")
            except Exception as e:
                print(f"❌ Delete failed: {e}")
        else:
            print("❌ Delete cancelled.")
    
    def run(self):
        """Run the interactive file browser."""
        print("🗂️  Runpod File Browser")
        print("=" * 30)
        
        if not self.select_volume():
            return
        
        while True:
            self.display_current_directory()
            
            print("\n🎛️  Actions:")
            print("  d <name>  - Navigate to directory")
            print("  u         - Go up one level")
            print("  dl <num>  - Download file")
            print("  rm <num>  - Delete file")
            print("  r         - Refresh")
            print("  q         - Quit")
            
            action = input("\n❓ Action: ").strip().split()
            
            if not action:
                continue
            
            command = action[0].lower()
            
            if command == 'q':
                print("👋 Goodbye!")
                break
            
            elif command == 'r':
                continue  # Refresh by looping
            
            elif command == 'u':
                self.go_up_directory()
            
            elif command == 'd' and len(action) > 1:
                dir_name = action[1]
                directories, _ = self.list_current_directory()
                if dir_name in directories:
                    self.navigate_to_directory(dir_name)
                else:
                    print(f"❌ Directory '{dir_name}' not found.")
            
            elif command == 'dl' and len(action) > 1:
                try:
                    file_num = int(action[1]) - 1
                    _, files = self.list_current_directory()
                    if 0 <= file_num < len(files):
                        self.download_file(files[file_num])
                    else:
                        print("❌ Invalid file number.")
                except ValueError:
                    print("❌ Invalid file number.")
            
            elif command == 'rm' and len(action) > 1:
                try:
                    file_num = int(action[1]) - 1
                    _, files = self.list_current_directory()
                    if 0 <= file_num < len(files):
                        self.delete_file(files[file_num])
                    else:
                        print("❌ Invalid file number.")
                except ValueError:
                    print("❌ Invalid file number.")
            
            else:
                print("❌ Unknown command. Use 'q' to quit.")


def browse_example():
    """Example: Browse files programmatically."""
    api = RunpodStorageAPI()
    
    # Get volumes
    volumes = api.list_volumes()
    if not volumes:
        print("❌ No volumes found.")
        return
    
    volume_id = volumes[0]['id']
    print(f"📁 Browsing volume: {volume_id}")
    
    # List root files
    files = api.list_files(volume_id)
    print(f"\n📄 Found {len(files)} files:")
    
    for file_info in files[:10]:  # Show first 10 files
        size_mb = file_info['size'] / (1024 * 1024)
        modified = file_info['last_modified'].strftime("%Y-%m-%d")
        print(f"  📄 {file_info['key']} ({size_mb:.2f} MB, {modified})")
    
    if len(files) > 10:
        print(f"  ... and {len(files) - 10} more files")


if __name__ == "__main__":
    # Check environment variables
    if not os.getenv("RUNPOD_API_KEY"):
        print("❌ Please set RUNPOD_API_KEY environment variable")
        exit(1)
    
    if not (os.getenv("RUNPOD_S3_ACCESS_KEY") and os.getenv("RUNPOD_S3_SECRET_KEY")):
        print("❌ Please set RUNPOD_S3_ACCESS_KEY and RUNPOD_S3_SECRET_KEY environment variables")
        exit(1)
    
    print("Choose an example:")
    print("1. Interactive file browser")
    print("2. Simple file listing")
    
    choice = input("Enter choice (1-2): ").strip()
    
    if choice == "1":
        browser = FileBrowser()
        browser.run()
    elif choice == "2":
        browse_example()
    else:
        print("❌ Invalid choice.")