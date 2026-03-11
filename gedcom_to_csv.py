#!/usr/bin/env python3
"""
Script to parse GEDCOM genealogy files and generate CSV files for family tree visualization
Generates two files:
1. fam_tree.csv - People and their family relationships
2. fam_tree_events.csv - Events (births, deaths, etc.) with geocoded locations

Installation:
    pip install python-gedcom geopy --break-system-packages

Usage:
    1. Update GEDCOM_PATH with your GEDCOM file location
    2. Run: python gedcom_to_csv.py
"""

from gedcom.parser import Parser
from gedcom.element.individual import IndividualElement
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
import csv

# Configuration
GEDCOM_PATH = "INSERT GEDCOM FILE HERE"  # Update this with your GEDCOM file path
OUTPUT_EVENTS = "fam_tree_events.csv"
OUTPUT_PEOPLE = "fam_tree.csv"
GEOCODE_CACHE = "geocoding_cache.csv"
MANUAL_COORDS = "manual_coordinates.csv"
GEOCODE_FAILURES = "geocoding_failures.csv"
GEOCODE_DELAY = 1.0  # Delay between geocoding requests to avoid rate limiting

def load_geocoding_cache():
    """Load previously geocoded locations from cache file"""
    cache = {}
    try:
        with open(GEOCODE_CACHE, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cache[row['place']] = {
                    'lon': float(row['lon']),
                    'lat': float(row['lat'])
                }
        print(f"✓ Loaded {len(cache)} locations from geocoding cache")
    except FileNotFoundError:
        print("ℹ️  No existing geocoding cache found (will create new one)")
    except Exception as e:
        print(f"⚠️  Error loading cache: {e}")
    return cache

def load_manual_coordinates():
    """Load manually corrected coordinates"""
    manual = {}
    try:
        with open(MANUAL_COORDS, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                manual[row['place']] = {
                    'lon': float(row['lon']),
                    'lat': float(row['lat'])
                }
        print(f"✓ Loaded {len(manual)} manual coordinate corrections")
    except FileNotFoundError:
        print("ℹ️  No manual coordinates file found")
    except Exception as e:
        print(f"⚠️  Error loading manual coordinates: {e}")
    return manual

def save_geocoding_cache(cache):
    """Save geocoding cache to file"""
    try:
        with open(GEOCODE_CACHE, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['place', 'lon', 'lat'])
            writer.writeheader()
            for place, coords in cache.items():
                if coords:  # Only save successful geocodes
                    writer.writerow({
                        'place': place,
                        'lon': coords['lon'],
                        'lat': coords['lat']
                    })
        print(f"✓ Saved {len([c for c in cache.values() if c])} locations to cache")
    except Exception as e:
        print(f"⚠️  Error saving cache: {e}")

def save_geocoding_failures(failures):
    """Save failed geocoding attempts for manual correction"""
    try:
        with open(GEOCODE_FAILURES, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['place'])
            writer.writeheader()
            for place in set(failures):
                writer.writerow({'place': place})
        print(f"✓ Saved {len(set(failures))} failed locations to {GEOCODE_FAILURES}")
        print(f"   Run fix_geocoding.py to manually correct these")
    except Exception as e:
        print(f"⚠️  Error saving failures: {e}")


# Load existing geocoding cache if it exists
print("Loading geocoding cache...")
geocoding_cache = {}
manual_coords = {}

# Load automatic geocoding cache
try:
    with open(GEOCODE_CACHE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            geocoding_cache[row['Place']] = {
                'lon': float(row['lon']),
                'lat': float(row['lat'])
            }
    print(f"✅ Loaded {len(geocoding_cache)} cached locations from {GEOCODE_CACHE}")
except FileNotFoundError:
    print(f"No existing cache found - will create {GEOCODE_CACHE}")

# Load manual coordinates (takes priority over cache)
try:
    with open(MANUAL_COORDS, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            manual_coords[row['Place']] = {
                'lon': float(row['lon']),
                'lat': float(row['lat'])
            }
    print(f"✅ Loaded {len(manual_coords)} manual coordinates from {MANUAL_COORDS}")
except FileNotFoundError:
    print(f"No manual coordinates found - you can create {MANUAL_COORDS} to override failed geocodes")

# Initialize parser
print("Parsing GEDCOM file...")
gedcom_parser = Parser()

# Set parser to be more lenient with format violations
gedcom_parser.strict = False  # Don't throw errors on format violations

try:
    gedcom_parser.parse_file(GEDCOM_PATH)
    print("✅ GEDCOM file parsed successfully")
except Exception as e:
    print(f"❌ Error parsing GEDCOM file: {e}")
    print("Try using a GEDCOM validator to fix format issues: https://chronoplexsoftware.com/gedcomvalidator/")
    exit(1)

# Lists to store data
people_data = []
events_data = []

# Get all individuals
root_child_elements = gedcom_parser.get_root_child_elements()

print("Extracting people and events...")
skipped_people = 0
skipped_events = 0

for element in root_child_elements:
    if isinstance(element, IndividualElement):
        try:
            # Get person info
            name = element.get_name()
            first_name = name[0] if name[0] else ""
            surname = name[1] if name[1] else ""
            gender = element.get_gender() if element.get_gender() else ""
            
            # Get family relationships
            fams_list = gedcom_parser.get_families(element, family_type='FAMS')
            fams = fams_list[0].get_pointer().replace('@', '') if fams_list else ''
            
            famc_list = gedcom_parser.get_families(element, family_type='FAMC')
            famc = famc_list[0].get_pointer().replace('@', '') if famc_list else ''
            
            # Get ancestors (for filtering)
            ancestors = gedcom_parser.get_ancestors(element)
            # Match original: get surnames only, remove duplicates
            ancestor_surnames = list(set([x.get_name()[1] for x in ancestors if x.get_name()[1]]))
            
            # Add to people data
            people_data.append({
                'Name': first_name,
                'Surname': surname,
                'Gender': gender,
                'FAMS': fams,
                'FAMC': famc,
                'Ancestors': str(ancestor_surnames)  # Convert list to string for CSV
            })
            
            # Get events for this person
            child_elements = element.get_child_elements()
            for child in child_elements:
                try:
                    event_type = child.get_tag()
                    
                    # Only process event types we care about
                    if event_type in ['BIRT', 'DEAT', 'MARR', 'ADDR', 'RESI', 'EMIG', 'IMMI']:
                        children = child.get_child_elements()
                        child_tags = [x.get_tag() for x in children]
                        
                        # Get date
                        date = ''
                        if 'DATE' in child_tags:
                            date = children[child_tags.index('DATE')].get_value()
                        
                        # Get place
                        place = ''
                        if 'PLAC' in child_tags:
                            place = children[child_tags.index('PLAC')].get_value()
                        
                        # Only add events that have both date and place
                        if date and place:
                            events_data.append({
                                'Name': first_name,
                                'Surname': surname,
                                'Gender': gender,
                                'Event_type': event_type,
                                'Date': date,
                                'Place': place,
                                'lon': None,  # Will be filled by geocoding
                                'lat': None
                            })
                except Exception as e:
                    skipped_events += 1
                    # Silently skip problematic events
                    continue
                    
        except Exception as e:
            skipped_people += 1
            # Silently skip problematic people
            continue

print(f"Found {len(people_data)} people and {len(events_data)} events")
if skipped_people > 0:
    print(f"⚠️  Skipped {skipped_people} people due to format errors")
if skipped_events > 0:
    print(f"⚠️  Skipped {skipped_events} events due to format errors")

# Geocode event locations (with caching for unique places)
print("\nGeocoding event locations...")

# Get unique places
unique_places = list(set([event['Place'] for event in events_data]))
print(f"Found {len(unique_places)} unique locations in dataset")

# Check how many are already cached
cached_count = sum(1 for place in unique_places if place in geocoding_cache or place in manual_coords)
needs_geocoding = [place for place in unique_places if place not in geocoding_cache and place not in manual_coords]

print(f"📦 {cached_count} locations already cached")
print(f"🔍 {len(needs_geocoding)} locations need geocoding")

# Initialize geocoder with proper User-Agent (required by OSM)
if needs_geocoding:
    geolocator = Nominatim(user_agent="family_tree_mapper")
    print("\nGeocoding new locations (this may take a while)...")
    print("Note: Using OpenStreetMap Nominatim (max 1 request/sec)")

# Create combined cache (manual takes priority)
place_cache = {}
geocoded_count = 0
failed_places = []
newly_geocoded = {}

# Use cached/manual coordinates first
for place in unique_places:
    if place in manual_coords:
        place_cache[place] = manual_coords[place]
        print(f"✓ Using manual coordinates for: {place}")
    elif place in geocoding_cache:
        place_cache[place] = geocoding_cache[place]

# Geocode new places
for i, place in enumerate(needs_geocoding):
    print(f"Geocoding {i+1}/{len(needs_geocoding)}: {place}")
    
    try:
        # Geocode with geopy
        location = geolocator.geocode(place, timeout=10)
        
        if location:
            coords = {'lon': location.longitude, 'lat': location.latitude}
            place_cache[place] = coords
            newly_geocoded[place] = coords
            geocoded_count += 1
            print(f"  ✓ Success")
        else:
            print(f"  ⚠️  Could not geocode: {place}")
            failed_places.append(place)
            place_cache[place] = None
        
        # Rate limiting delay (OSM Nominatim requires 1 req/sec max)
        time.sleep(GEOCODE_DELAY)
        
    except GeocoderTimedOut:
        print(f"  ⏱️  Timeout for {place} - retrying...")
        try:
            # Retry once on timeout
            time.sleep(2)
            location = geolocator.geocode(place, timeout=15)
            if location:
                coords = {'lon': location.longitude, 'lat': location.latitude}
                place_cache[place] = coords
                newly_geocoded[place] = coords
                geocoded_count += 1
                print(f"  ✓ Success (retry)")
            else:
                failed_places.append(place)
                place_cache[place] = None
        except Exception as e:
            print(f"  ❌ Retry failed: {e}")
            failed_places.append(place)
            place_cache[place] = None
            
    except GeocoderServiceError as e:
        print(f"  ❌ Service error for {place}: {e}")
        failed_places.append(place)
        place_cache[place] = None
        
    except Exception as e:
        print(f"  ❌ Error geocoding {place}: {e}")
        failed_places.append(place)
        place_cache[place] = None

print(f"\n✅ Successfully geocoded {geocoded_count} new locations")
print(f"📦 Total cached: {len([p for p in place_cache if place_cache[p] is not None])}")

# Save newly geocoded places to cache
if newly_geocoded:
    print(f"\nSaving {len(newly_geocoded)} new coordinates to cache...")
    
    # Append to existing cache file
    file_exists = geocoding_cache  # True if we loaded existing cache
    with open(GEOCODE_CACHE, 'a' if file_exists else 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['Place', 'lon', 'lat'])
        if not file_exists:
            writer.writeheader()
        for place, coords in newly_geocoded.items():
            writer.writerow({'Place': place, 'lon': coords['lon'], 'lat': coords['lat']})
    
    print(f"✅ Cache updated: {GEOCODE_CACHE}")

# Save failed places for manual correction
if failed_places:
    print(f"\n⚠️  Failed to geocode {len(failed_places)} unique places")
    
    with open(GEOCODE_FAILURES, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Place'])
        for place in set(failed_places):
            writer.writerow([place])
    
    print(f"💾 Failed locations saved to: {GEOCODE_FAILURES}")
    print(f"\nYou can manually add coordinates to '{MANUAL_COORDS}' using this format:")
    print("Place,lon,lat")
    print('"New York, USA",-74.006,40.713')
    print("\nThen re-run this script - it will use your manual coordinates!")

# Apply cached coordinates to all events
print("\nApplying coordinates to events...")
for event in events_data:
    cached = place_cache.get(event['Place'])
    if cached:
        event['lon'] = cached['lon']
        event['lat'] = cached['lat']

if failed_places:
    print(f"\n⚠️  Failed to geocode {len(failed_places)} unique places:")
    for place in set(failed_places):
        print(f"  - {place}")
    print("\nYou may want to manually add coordinates for these places.")

# Remove events without coordinates
events_data = [e for e in events_data if e['lon'] is not None and e['lat'] is not None]

# Write fam_tree.csv
print(f"\nWriting {OUTPUT_PEOPLE}...")
with open(OUTPUT_PEOPLE, 'w', newline='', encoding='utf-8') as f:
    if people_data:
        writer = csv.DictWriter(f, fieldnames=['Name', 'Surname', 'Gender', 'FAMS', 'FAMC', 'Ancestors'])
        writer.writeheader()
        writer.writerows(people_data)

print(f"✅ Wrote {len(people_data)} people to {OUTPUT_PEOPLE}")

# Write fam_tree_events.csv
print(f"\nWriting {OUTPUT_EVENTS}...")
with open(OUTPUT_EVENTS, 'w', newline='', encoding='utf-8') as f:
    if events_data:
        writer = csv.DictWriter(f, fieldnames=['Name', 'Gender', 'Event_type', 'Date', 'Place', 'lon', 'lat', 'Surname'])
        writer.writeheader()
        writer.writerows(events_data)

print(f"✅ Wrote {len(events_data)} events to {OUTPUT_EVENTS}")

print("\n🎉 Done! You can now use these CSV files with your family tree map.")
