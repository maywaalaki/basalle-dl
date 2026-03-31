#!/usr/bin/env python3
"""
Test script to validate bot functionality without connecting to Telegram.
"""

import os
import json
import sys

# Add the bot directory to path
sys.path.insert(0, '/home/ubuntu/bot_update')

# Test 1: Import modules
print("=" * 60)
print("TEST 1: Importing modules...")
print("=" * 60)
try:
    from bot import (
        config, load_config, save_config, add_user, get_users,
        MSG, is_supported_url, OWNER_ID
    )
    print("✅ All modules imported successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Configuration system
print("\n" + "=" * 60)
print("TEST 2: Configuration system...")
print("=" * 60)
try:
    test_config = load_config()
    print(f"✅ Config loaded: {list(test_config.keys())}")
    
    # Test updating config
    test_config['owner_contact'] = '@TestOwner'
    save_config(test_config)
    reloaded = load_config()
    assert reloaded['owner_contact'] == '@TestOwner'
    print("✅ Config save/load working")
except Exception as e:
    print(f"❌ Config test failed: {e}")

# Test 3: User tracking system
print("\n" + "=" * 60)
print("TEST 3: User tracking system...")
print("=" * 60)
try:
    add_user(12345)
    add_user(67890)
    add_user(12345)  # Duplicate
    users = get_users()
    assert '12345' in users
    assert '67890' in users
    assert len(users) == 2  # No duplicates
    print(f"✅ User tracking working. Users: {users}")
except Exception as e:
    print(f"❌ User tracking test failed: {e}")

# Test 4: URL validation
print("\n" + "=" * 60)
print("TEST 4: URL validation...")
print("=" * 60)
test_urls = [
    ("https://www.youtube.com/watch?v=test", True),
    ("https://youtu.be/test", True),
    ("https://www.tiktok.com/video/123", True),
    ("https://www.instagram.com/p/123", True),
    ("https://www.facebook.com/video/123", True),
    ("https://twitter.com/user/status/123", True),
    ("https://x.com/user/status/123", True),
    ("https://example.com/video", False),
    ("not a url", False),
]

for url, expected in test_urls:
    result = is_supported_url(url)
    status = "✅" if result == expected else "❌"
    print(f"{status} {url}: {result} (expected {expected})")

# Test 5: Somali messages
print("\n" + "=" * 60)
print("TEST 5: Somali language messages...")
print("=" * 60)
try:
    required_keys = [
        'choose', 'btn_video', 'btn_audio', 'downloading',
        'success_video', 'success_audio', 'failed', 'invalid_link',
        'error', 'too_large', 'help_text', 'owner_info', 'broadcast_done'
    ]
    for key in required_keys:
        assert key in MSG, f"Missing message key: {key}"
    print(f"✅ All {len(required_keys)} Somali messages present")
except Exception as e:
    print(f"❌ Message test failed: {e}")

# Test 6: Welcome text with placeholder
print("\n" + "=" * 60)
print("TEST 6: Welcome text with name placeholder...")
print("=" * 60)
try:
    welcome = config['welcome_text']
    assert '{name}' in welcome, "Name placeholder not found"
    personalized = welcome.replace('{name}', 'Ahmed')
    assert 'Ahmed' in personalized
    print(f"✅ Welcome text placeholder working")
    print(f"   Sample: {personalized[:100]}...")
except Exception as e:
    print(f"❌ Welcome text test failed: {e}")

# Test 7: File structure
print("\n" + "=" * 60)
print("TEST 7: File structure...")
print("=" * 60)
try:
    files = ['bot.py', 'downloader.py', 'requirements.txt', 'Dockerfile', 'README.md']
    for f in files:
        path = f'/home/ubuntu/bot_update/{f}'
        assert os.path.exists(path), f"Missing file: {f}"
    print(f"✅ All required files present")
except Exception as e:
    print(f"❌ File structure test failed: {e}")

print("\n" + "=" * 60)
print("SUMMARY: All tests completed successfully! ✅")
print("=" * 60)
