#!/usr/bin/env python3
"""
Evidence frame verification utility.

Validates evidence directory layout, frame counts, and metadata completeness.
"""

import os
import json
from pathlib import Path
from datetime import datetime

EVIDENCE_DIR = Path("new_version/server/evidence_frames")

def check_evidence_structure():
    """Inspect directory structure and summarize recent warning captures."""
    
    print("=" * 80)
    print("EVIDENCE FRAMES VERIFICATION REPORT")
    print("=" * 80)
    print(f"Evidence Root: {EVIDENCE_DIR.absolute()}\n")
    
    if not EVIDENCE_DIR.exists():
        print("❌ Evidence directory does not exist!")
        return
    
    print("✅ Evidence directory found\n")
    
    # Traverse nested evidence directories.
    for username_dir in sorted(EVIDENCE_DIR.iterdir()):
        if not username_dir.is_dir():
            continue
        
        username = username_dir.name
        print(f"\n📁 Username: {username}")
        
        for testid_dir in sorted(username_dir.iterdir()):
            if not testid_dir.is_dir():
                continue
                
            testid = testid_dir.name
            print(f"  📁 TestID: {testid}")
            
            for sectionid_dir in sorted(testid_dir.iterdir()):
                if not sectionid_dir.is_dir():
                    continue
                    
                sectionid = sectionid_dir.name
                print(f"    📁 SectionID: {sectionid}")
                
                # Warning directories are timestamped capture groups.
                warning_dirs = [d for d in sectionid_dir.iterdir() if d.is_dir()]
                print(f"      └─ Warnings Captured: {len(warning_dirs)}")
                
                # Show only the latest three warning groups for readability.
                for warning_dir in sorted(warning_dirs)[-3:]:
                    warning_time = warning_dir.name
                    
                    # Count captured JPEG frames.
                    jpeg_files = list(warning_dir.glob("*.jpg"))
                    
                    # Validate metadata and frame index files.
                    metadata_file = warning_dir / "metadata.json"
                    frames_index = warning_dir / "frames.txt"
                    
                    print(f"        ├─ Warning Time: {warning_time}")
                    print(f"        │  ├─ JPEG Frames: {len(jpeg_files)}")
                    print(f"        │  ├─ Metadata: {'✅' if metadata_file.exists() else '❌'}")
                    print(f"        │  └─ Index: {'✅' if frames_index.exists() else '❌'}")
                    
                    # Print selected metadata fields when available.
                    if metadata_file.exists():
                        try:
                            with open(metadata_file) as f:
                                metadata = json.load(f)
                            print(f"        │     └─ Warning: {metadata.get('warning_text', 'N/A')}")
                            print(f"        │     └─ Vision Stats: {list(metadata.get('vision_stats', {}).keys())}")
                        except Exception as e:
                            print(f"        │     └─ Error reading metadata: {e}")
                    
                    # Show aggregate frame size statistics.
                    if jpeg_files:
                        total_size = sum(f.stat().st_size for f in jpeg_files)
                        avg_size = total_size / len(jpeg_files)
                        print(f"        │     └─ Total Size: {total_size / 1024:.1f} KB (avg {avg_size / 1024:.1f} KB per frame)")


def verify_frame_counts():
    """Verify that evidence captures contain the expected 20 frames."""
    
    print("\n" + "=" * 80)
    print("FRAME COUNT VERIFICATION")
    print("=" * 80 + "\n")
    
    frame_stats = {
        "total_warnings": 0,
        "with_correct_count": 0,
        "with_incorrect_count": 0,
        "frame_counts": {}
    }
    
    for username_dir in EVIDENCE_DIR.rglob("*"):
        if not username_dir.parent.name.startswith("metadata"):
            continue
            
        warning_dirs = [d for d in username_dir.parent.parent.iterdir() if d.is_dir()]
        
        for warning_dir in warning_dirs:
            jpeg_files = list(warning_dir.glob("*.jpg"))
            frame_count = len(jpeg_files)
            
            frame_stats["total_warnings"] += 1
            
            if frame_count not in frame_stats["frame_counts"]:
                frame_stats["frame_counts"][frame_count] = 0
            frame_stats["frame_counts"][frame_count] += 1
            
            if frame_count == 20:
                frame_stats["with_correct_count"] += 1
            else:
                frame_stats["with_incorrect_count"] += 1
                # Display only a small sample of mismatches.
                if frame_stats["with_incorrect_count"] <= 5:
                    print(f"⚠️  {warning_dir.relative_to(EVIDENCE_DIR)}: {frame_count} frames (expected 20)")
    
    print(f"\n✅ Total Warnings Captured: {frame_stats['total_warnings']}")
    print(f"✅ With Correct Count (20): {frame_stats['with_correct_count']}")
    if frame_stats["with_incorrect_count"] > 0:
        print(f"❌ With Incorrect Count: {frame_stats['with_incorrect_count']}")
    print(f"\nFrame Count Distribution: {frame_stats['frame_counts']}")


def verify_metadata():
    """Check metadata files for required fields."""
    
    print("\n" + "=" * 80)
    print("METADATA VERIFICATION")
    print("=" * 80 + "\n")
    
    metadata_stats = {
        "total_files": 0,
        "with_all_fields": 0,
        "missing_fields": {}
    }
    
    required_fields = ["username", "testid", "sectionid", "warning_text", "timestamp_warning", "frames_data"]
    
    for metadata_file in EVIDENCE_DIR.rglob("metadata.json"):
        metadata_stats["total_files"] += 1
        
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            missing = [field for field in required_fields if field not in metadata]
            
            if not missing:
                metadata_stats["with_all_fields"] += 1
            else:
                for field in missing:
                    metadata_stats["missing_fields"][field] = metadata_stats["missing_fields"].get(field, 0) + 1
                    
        except Exception as e:
            print(f"❌ Error reading {metadata_file}: {e}")
    
    print(f"✅ Total Metadata Files: {metadata_stats['total_files']}")
    print(f"✅ With All Required Fields: {metadata_stats['with_all_fields']}")
    
    if metadata_stats["missing_fields"]:
        print(f"❌ Missing Fields Summary:")
        for field, count in metadata_stats["missing_fields"].items():
            print(f"   - {field}: {count} files")
    else:
        print("✅ All metadata files complete!")


if __name__ == "__main__":
    if EVIDENCE_DIR.exists():
        check_evidence_structure()
        verify_frame_counts()
        verify_metadata()
        print("\n" + "=" * 80)
        print("VERIFICATION COMPLETE")
        print("=" * 80)
    else:
        print(f"❌ Evidence directory not found: {EVIDENCE_DIR.absolute()}")
        print("Make sure the path is correct relative to where you run the script.")
