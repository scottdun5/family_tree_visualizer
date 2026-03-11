#!/usr/bin/env python3
"""
Interactive tool to manually correct failed geocoding attempts.

Usage:
    python fix_geocoding.py

This script reads geocoding_failures.csv and helps you:
1. Try variations of the address
2. Get suggestions from OpenStreetMap
3. Manually enter coordinates
4. Preview locations before saving

Results are saved to manual_coordinates.csv
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
import csv
import time

GEOCODE_FAILURES = "geocoding_failures.csv"
MANUAL_COORDS = "manual_coordinates.csv"
GEOCODE_DELAY = 1.0

# Initialize geocoder
geolocator = Nominatim(user_agent="family_tree_mapper_fixer")

def load_failures():
    """Load failed geocoding attempts"""
    failures = []
    try:
        with open(GEOCODE_FAILURES, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                failures.append(row['Place'])
        return failures
    except FileNotFoundError:
        print(f"❌ Could not find {GEOCODE_FAILURES}")
        print("Run gedcom_to_csv.py first to generate failed locations.")
        return None

def load_existing_manual():
    """Load existing manual coordinates to avoid duplicates"""
    manual = {}
    try:
        with open(MANUAL_COORDS, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                manual[row['Place']] = (float(row['lon']), float(row['lat']))
    except FileNotFoundError:
        pass
    return manual

def save_manual_coord(place, lon, lat):
    """Append a manual coordinate to the file"""
    # Check if file exists to decide on write mode
    try:
        with open(MANUAL_COORDS, 'r') as f:
            file_exists = True
    except FileNotFoundError:
        file_exists = False
    
    with open(MANUAL_COORDS, 'a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Place', 'lon', 'lat'])
        if not file_exists:
            writer.writeheader()
        writer.writerow({'Place': place, 'lon': lon, 'lat': lat})

def try_variations(place):
    """Try common variations of an address"""
    print(f"\n🔍 Trying variations for: {place}")
    
    variations = [
        place,  # Original
        place.split(',')[0] if ',' in place else place,  # Just first part
        ', '.join(place.split(',')[-2:]) if place.count(',') >= 2 else place,  # Last two parts
        place.replace('County', '').strip(),  # Remove "County"
        place.replace('Borough', '').strip(),  # Remove "Borough"
    ]
    
    # Remove duplicates while preserving order
    seen = set()
    variations = [x for x in variations if not (x in seen or seen.add(x))]
    
    results = []
    for i, var in enumerate(variations, 1):
        if var == place:
            print(f"  {i}. {var} (original)")
        else:
            print(f"  {i}. {var}")
        
        try:
            location = geolocator.geocode(var, timeout=10, exactly_one=False, limit=3)
            time.sleep(GEOCODE_DELAY)
            
            if location:
                if isinstance(location, list):
                    for j, loc in enumerate(location):
                        results.append({
                            'variation': var,
                            'display': loc.address,
                            'lon': loc.longitude,
                            'lat': loc.latitude
                        })
                        if j < 2:  # Show first 2 matches
                            print(f"     ✓ Found: {loc.address}")
                else:
                    results.append({
                        'variation': var,
                        'display': location.address,
                        'lon': location.longitude,
                        'lat': location.latitude
                    })
                    print(f"     ✓ Found: {location.address}")
            else:
                print(f"     ✗ No results")
                
        except GeocoderTimedOut:
            print(f"     ⏱️  Timeout")
        except Exception as e:
            print(f"     ❌ Error: {e}")
    
    return results

def fix_location(place, existing_manual):
    """Interactive fixing for a single location"""
    print("\n" + "="*80)
    print(f"📍 LOCATION: {place}")
    print("="*80)
    
    # Check if already manually fixed
    if place in existing_manual:
        lon, lat = existing_manual[place]
        print(f"✓ Already fixed: lon={lon}, lat={lat}")
        choice = input("\nOverwrite? (y/n): ").lower()
        if choice != 'y':
            return
    
    # Try variations
    results = try_variations(place)
    
    if results:
        print(f"\n✅ Found {len(results)} possible matches:")
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['display']}")
            print(f"     Coordinates: {result['lon']:.4f}, {result['lat']:.4f}")
            print(f"     Google Maps: https://www.google.com/maps?q={result['lat']},{result['lon']}")
        
        print(f"  {len(results)+1}. Try a different search")
        print(f"  {len(results)+2}. Enter coordinates manually")
        print(f"  {len(results)+3}. Skip this location")
        
        choice = input(f"\nSelect option (1-{len(results)+3}): ").strip()
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(results):
                result = results[choice_num - 1]
                save_manual_coord(place, result['lon'], result['lat'])
                print(f"✅ Saved: {place} -> {result['lon']:.4f}, {result['lat']:.4f}")
                return
            elif choice_num == len(results) + 1:
                # Try custom search
                custom = input("Enter custom search term: ").strip()
                if custom:
                    try_custom(place, custom)
                    return
            elif choice_num == len(results) + 2:
                # Manual entry
                manual_entry(place)
                return
            else:
                print("⏭️  Skipping...")
                return
        except ValueError:
            print("❌ Invalid choice. Skipping...")
            return
    else:
        print("\n❌ No matches found")
        print("Options:")
        print("  1. Try a different search")
        print("  2. Enter coordinates manually")
        print("  3. Skip this location")
        
        choice = input("Select option (1-3): ").strip()
        
        if choice == '1':
            custom = input("Enter custom search term: ").strip()
            if custom:
                try_custom(place, custom)
        elif choice == '2':
            manual_entry(place)
        else:
            print("⏭️  Skipping...")

def try_custom(original_place, search_term):
    """Try a custom search term"""
    print(f"\n🔍 Searching for: {search_term}")
    
    try:
        location = geolocator.geocode(search_term, timeout=10, exactly_one=False, limit=5)
        time.sleep(GEOCODE_DELAY)
        
        if location:
            if not isinstance(location, list):
                location = [location]
            
            print(f"\n✅ Found {len(location)} results:")
            for i, loc in enumerate(location, 1):
                print(f"  {i}. {loc.address}")
                print(f"     Coordinates: {loc.longitude:.4f}, {loc.latitude:.4f}")
                print(f"     Google Maps: https://www.google.com/maps?q={loc.latitude},{loc.longitude}")
            
            print(f"  {len(location)+1}. None of these")
            
            choice = input(f"\nSelect result (1-{len(location)+1}): ").strip()
            
            try:
                choice_num = int(choice)
                if 1 <= choice_num <= len(location):
                    loc = location[choice_num - 1]
                    save_manual_coord(original_place, loc.longitude, loc.latitude)
                    print(f"✅ Saved: {original_place} -> {loc.longitude:.4f}, {loc.latitude:.4f}")
                else:
                    print("⏭️  Skipping...")
            except ValueError:
                print("❌ Invalid choice. Skipping...")
        else:
            print("❌ No results found")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def manual_entry(place):
    """Manually enter coordinates"""
    print(f"\n📝 Manual entry for: {place}")
    print("Tip: You can find coordinates at https://www.google.com/maps")
    print("      Right-click on the location and copy the coordinates")
    
    try:
        lon = float(input("Longitude (e.g., -74.006): ").strip())
        lat = float(input("Latitude (e.g., 40.713): ").strip())
        
        print(f"\nPreview: https://www.google.com/maps?q={lat},{lon}")
        confirm = input("Save these coordinates? (y/n): ").lower()
        
        if confirm == 'y':
            save_manual_coord(place, lon, lat)
            print(f"✅ Saved: {place} -> {lon:.4f}, {lat:.4f}")
        else:
            print("⏭️  Cancelled")
    except ValueError:
        print("❌ Invalid coordinates. Skipping...")

def main():
    print("=" * 80)
    print("GEOCODING FAILURE FIXER")
    print("=" * 80)
    
    # Load failures
    failures = load_failures()
    if failures is None:
        return
    
    if not failures:
        print("✅ No failed locations to fix!")
        return
    
    print(f"\nFound {len(failures)} failed locations")
    
    # Load existing manual coordinates
    existing_manual = load_existing_manual()
    if existing_manual:
        print(f"ℹ️  {len(existing_manual)} locations already manually fixed")
    
    # Filter out already fixed
    remaining = [f for f in failures if f not in existing_manual]
    if not remaining:
        print("✅ All locations already fixed!")
        return
    
    print(f"📋 {len(remaining)} locations need fixing\n")
    
    # Process each failure
    for i, place in enumerate(remaining, 1):
        print(f"\n[{i}/{len(remaining)}]")
        fix_location(place, existing_manual)
        
        if i < len(remaining):
            cont = input("\nContinue to next location? (y/n/q to quit): ").lower()
            if cont == 'q':
                print("\n👋 Exiting...")
                break
            elif cont != 'y':
                print("\n👋 Exiting...")
                break
    
    print("\n" + "=" * 80)
    print("✅ DONE!")
    print("=" * 80)
    print(f"\nManual coordinates saved to: {MANUAL_COORDS}")
    print("Run gedcom_to_csv.py again to apply these corrections!")

if __name__ == "__main__":
    main()
