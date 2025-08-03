#!/usr/bin/env python3
"""
Example: Complete Volume Management with Runpod Storage

This example demonstrates how to create, update, and delete network volumes
using the Runpod Storage API.
"""

import os

from runpod_storage import RunpodStorageAPI


def create_volume_example():
    """Create a new network volume."""
    api = RunpodStorageAPI()

    print("🔨 Creating a new network volume...")

    try:
        volume = api.create_volume(
            name="example-volume",
            size=20,  # Start with 20GB
            datacenter="EU-RO-1",  # European datacenter
        )

        print("✅ Volume created successfully!")
        print(f"  📊 ID: {volume['id']}")
        print(f"  📛 Name: {volume['name']}")
        print(f"  💾 Size: {volume['size']} GB")
        print(f"  🌍 Datacenter: {volume['dataCenterId']}")

        return volume["id"]

    except Exception as e:
        print(f"❌ Failed to create volume: {e}")
        return None


def list_volumes_example():
    """List all network volumes."""
    api = RunpodStorageAPI()

    print("\n📋 Listing all network volumes...")

    try:
        volumes = api.list_volumes()

        if not volumes:
            print("📭 No volumes found.")
            return []

        print(f"📊 Found {len(volumes)} volume(s):")
        for i, volume in enumerate(volumes, 1):
            print(f"  {i}. {volume['id']}")
            print(f"     📛 Name: {volume.get('name', 'Unnamed')}")
            print(f"     💾 Size: {volume.get('size', 'Unknown')} GB")
            print(f"     🌍 Datacenter: {volume.get('dataCenterId', 'Unknown')}")
            print()

        return volumes

    except Exception as e:
        print(f"❌ Failed to list volumes: {e}")
        return []


def update_volume_example(volume_id):
    """Update an existing volume (rename and expand)."""
    api = RunpodStorageAPI()

    print(f"\n🔄 Updating volume {volume_id}...")

    try:
        # First, rename the volume
        print("📝 Renaming volume...")
        updated_volume = api.update_volume(volume_id, name="renamed-example-volume")
        print(f"✅ Renamed to: {updated_volume['name']}")

        # Then, expand the size
        print("📈 Expanding volume size...")
        expanded_volume = api.update_volume(volume_id, size=50)  # Expand to 50GB
        print(f"✅ Expanded to: {expanded_volume['size']} GB")

        # Finally, update both name and size
        print("🔄 Updating both name and size...")
        final_volume = api.update_volume(
            volume_id, name="large-example-volume", size=100  # Expand to 100GB
        )

        print("✅ Final update completed!")
        print(f"  📛 Name: {final_volume['name']}")
        print(f"  💾 Size: {final_volume['size']} GB")
        print(f"  🌍 Datacenter: {final_volume['dataCenterId']}")

    except Exception as e:
        print(f"❌ Failed to update volume: {e}")


def delete_volume_example(volume_id):
    """Delete a volume (with safety confirmation)."""
    api = RunpodStorageAPI()

    print(f"\n🗑️  Preparing to delete volume {volume_id}...")

    # In a real application, you'd want user confirmation
    print("⚠️  WARNING: This will permanently delete the volume and all data!")
    print("💡 TIP: In the interactive CLI, you get multiple confirmation prompts")

    # For this example, let's just show how it would work
    # Uncomment the next lines to actually delete:

    # try:
    #     success = api.delete_volume(volume_id)
    #     if success:
    #         print("✅ Volume deleted successfully!")
    #     else:
    #         print("❌ Volume not found or already deleted.")
    # except Exception as e:
    #     print(f"❌ Failed to delete volume: {e}")

    print("🛡️  For safety, actual deletion is commented out in this example")
    print("🎛️  Use the interactive CLI for safe volume deletion with confirmations")


def volume_size_limits_example():
    """Demonstrate volume size limits and validation."""
    api = RunpodStorageAPI()

    print("\n📏 Volume Size Limits and Validation:")
    print("=" * 50)

    # Show valid size ranges
    print("✅ Valid size ranges:")
    print("  • Minimum: 10 GB")
    print("  • Maximum: 4,000 GB (4 TB)")
    print("  • Updates: Can only increase size, not decrease")

    # Example of validation errors
    print("\n❌ These operations would fail:")
    print("  • Creating volume with size < 10 GB")
    print("  • Creating volume with size > 4000 GB")
    print("  • Updating volume to smaller size")

    # Show practical examples
    print("\n💡 Practical sizing examples:")
    sizes = [
        (20, "Small project files"),
        (100, "Medium dataset storage"),
        (500, "Large ML training data"),
        (1000, "Enterprise backup storage"),
        (4000, "Maximum volume size"),
    ]

    for size, description in sizes:
        print(f"  • {size:4d} GB - {description}")


def main():
    """Run all volume management examples."""
    print("🚀 Runpod Storage Volume Management Examples")
    print("=" * 60)

    # Check environment variables
    if not os.getenv("RUNPOD_API_KEY"):
        print("❌ Please set RUNPOD_API_KEY environment variable")
        return

    # 1. Show size limits
    volume_size_limits_example()

    # 2. List existing volumes
    existing_volumes = list_volumes_example()

    # 3. Create a new volume
    volume_id = create_volume_example()

    if volume_id:
        # 4. Update the volume
        update_volume_example(volume_id)

        # 5. Show how to delete (safely)
        delete_volume_example(volume_id)

    print("\n🎉 Volume management examples completed!")
    print("💡 Try the interactive CLI for hands-on volume management:")
    print("   runpod-storage interactive")


if __name__ == "__main__":
    main()
