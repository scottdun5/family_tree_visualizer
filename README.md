# Family Tree Geographic Visualizer

An interactive web application for visualizing family tree events (births, deaths, marriages, migrations) on a geographic map over time. Built with React, Mapbox GL JS, and Python.

![Family Tree Map Demo](screenshot.png)

## Why I Built This

While researching my family history, I wanted to answer questions that existing genealogy tools couldn't:

- **Where were my ancestors actually living at specific points in time?** Traditional family tree software shows relationships and vital records, but not geographic snapshots. I wanted to see where everyone was during major historical events—the 1918 flu pandemic, the Great Depression, World War II.

- **How did different branches of my family spread geographically?** Some surnames stayed clustered in one region for generations, while others dispersed widely. I wanted to visualize these patterns and understand migration trends across different family lines.

- **What were the street-level details?** Historical census records often include specific addresses. I wanted to map these down to the block level to see exactly where families lived, worked, and clustered—sometimes discovering that distant relatives lived just streets apart without knowing it.

After searching for tools that could provide this temporal-geographic view and finding none, I built this application. The Timeline View mode was specifically designed to answer "where was everyone in my tree on this date?"—a question that became the core feature driving the entire project.

## Features

### Interactive Map Visualization
- **Geographic Event Mapping**: Plot births, deaths, marriages, addresses, arrivals, and departures on an interactive world map
- **Timeline Slider**: Scrub through time to see events appear chronologically
- **Two Display Modes**:
  - **All Events Mode**: Shows cumulative history (all events up to selected date)
  - **Timeline View**: Shows only the most recent event per person (snapshot of where people were at that moment)

### Advanced Filtering
- **Event Type Filters**: Toggle visibility by event type (Birth, Death, Marriage, Address, Departure, Arrival, Other)
- **Surname Filters**: Filter by family surnames with searchable dropdown
- **Smart Timeline Logic**: Automatically hides likely-deceased individuals (90+ years since birth, or 80+ years since last event)

### Data Visualization
- **Color-Coded Events**: Green (births), Red (deaths), Pink (marriages), etc.
- **Hover Tooltips**: View detailed event information on mouseover
- **Multi-Event Handling**: Groups multiple events at same location for easy viewing
- **Event Statistics**: Real-time count of visible events

## Tech Stack

- **Frontend**: React 18, Mapbox GL JS v3
- **Data Processing**: Python 3 with python-gedcom, geopy
- **Data Format**: GEDCOM (genealogy standard) → CSV
- **Geocoding**: OpenStreetMap Nominatim (free, no API key required)

## Prerequisites

- **Node.js** or **Python 3** (for local server)
- **Mapbox account** (free tier: https://account.mapbox.com/)
- **GEDCOM file** from your genealogy software (Ancestry.com, MyHeritage, etc.)

## Installation & Setup

### Step 1: Generate CSV Files from GEDCOM

1. **Install Python dependencies:**
```bash
pip install python-gedcom geopy --break-system-packages
```

2. **Configure the Python script:**
   - Open `gedcom_to_csv.py`
   - Update `GEDCOM_PATH` with your GEDCOM file location

3. **Run the script:**
```bash
python gedcom_to_csv.py
```

This will generate:
- `fam_tree.csv` - People and family relationships
- `fam_tree_events.csv` - Events with geocoded coordinates
- `geocoding_cache.csv` - Cache of successfully geocoded locations
- `geocoding_failures.csv` - Locations that failed to geocode (if any)

**Note**: Geocoding 500-1000 unique locations takes ~8-15 minutes on first run (respects OpenStreetMap's 1 req/sec rate limit). Subsequent runs are nearly instant thanks to caching!

#### Fixing Failed Geocoding (Optional)

Some locations may fail to geocode due to typos, old addresses, or missing data. To fix these:

1. **Run the interactive fixer:**
```bash
python fix_geocoding.py
```

2. **The tool will help you:**
   - Try address variations automatically
   - Show multiple possible matches
   - Let you try custom search terms
   - Allow manual coordinate entry
   - Preview locations on Google Maps

3. **Re-run the main script:**
```bash
python gedcom_to_csv.py
```

The script will now use your manual corrections and the cache, processing only new locations. The second run takes ~1 minute instead of 10+ minutes!

### Step 2: Set Up the Web Application

1. **Get your Mapbox token:**
   - Sign up at https://account.mapbox.com/
   - Copy your "Default public token" (starts with `pk.`)

2. **Configure the app:**
   - Open `family-tree-map-canvas.html`
   - Find line 44: `const MAPBOX_TOKEN = 'YOUR_MAPBOX_TOKEN_HERE';`
   - Replace with your actual token

3. **Place files in same directory:**
```
your-project-folder/
├── family-tree-map-canvas.html
├── fam_tree_events.csv
├── fam_tree.csv
└── gedcom_to_csv.py
```

### Step 3: Run the Application

You **must** use a local server (not `file://`):

**Option A - Python:**
```bash
python -m http.server 8000
# or
python3 -m http.server 8000
```

**Option B - Node.js:**
```bash
npx http-server
```

**Option C - VS Code:**
- Install "Live Server" extension
- Right-click `family-tree-map-canvas.html` → "Open with Live Server"

Then open: `http://localhost:8000/family-tree-map-canvas.html`

## Usage Guide

### Display Modes

**📚 All Events Mode** (Default)
- Shows cumulative history
- All events appear as timeline progresses
- Best for: Seeing complete family migration patterns

**⏱️ Timeline View**
- Shows snapshot of where people were at selected date
- Displays only most recent event per person
- Hides deceased individuals (death + 5 years, or 90+ years old)
- Best for: Understanding family geography at specific moments

### Filtering Options

1. **Timeline Slider**: Drag to select any date between your earliest and latest events
2. **Event Type Filter**: Click legend items to show/hide event types
3. **Surname Filter**: 
   - Click search box to see all surnames
   - Type to search
   - Select multiple families
   - Click "Clear" to reset

### Event Colors

- 🎂 **Green**: Births
- ✝️ **Red**: Deaths  
- 💑 **Pink**: Marriages
- 🏠 **Purple**: Addresses
- ✈️ **Orange**: Departures
- 🛬 **Cyan**: Arrivals
- 📅 **Gray**: Other events

### Troubleshooting

**Map doesn't load:**
- Check browser console (F12) for errors
- Verify Mapbox token is correct
- Ensure you're using a local server (not opening file directly)

**CSV files not loading:**
- Ensure CSV files are in same directory as HTML file
- Check browser console for CORS errors
- Verify file names match exactly: `fam_tree.csv` and `fam_tree_events.csv`

**Geocoding failures:**
- Some locations may not be found in OpenStreetMap database
- Check console output for list of failed locations
- You can manually add coordinates to CSV file if needed
- Common issues: Typos, old addresses, renamed locations

**Performance issues:**
- Large datasets (10,000+ events) may be slow
- Try filtering by surname or event type
- Timeline View is faster than All Events mode

## Data Format

### fam_tree.csv
```csv
Name,Surname,Gender,FAMS,FAMC,Ancestors
John,Smith,M,F1,F2,"['Smith', 'Jones']"
```

### fam_tree_events.csv
```csv
Name,Gender,Event_type,Date,Place,lon,lat,Surname
John,M,BIRT,22 AUG 1904,"New York, USA",-74.006,40.713,Smith
```

## Customization

### Add New Event Types

Edit `family-tree-map-canvas.html`, find `EVENT_TYPES` object:

```javascript
const EVENT_TYPES = {
    'BIRT': { label: 'Birth', color: '#4CAF50', icon: '🎂' },
    'YOUR_TYPE': { label: 'Your Label', color: '#HEXCOLOR', icon: '📍' }
};
```

### Adjust Timeline Logic

Find `getFilteredEventsByMode()` function to modify:
- Death event retention period (default: 5 years)
- Age assumption for deceased (default: 90 years since birth, 80 years since last event)

### Change Map Style

Replace `'mapbox://styles/mapbox/dark-v11'` with other Mapbox styles:
- `streets-v12` - Light streets
- `satellite-v9` - Satellite imagery
- `outdoors-v12` - Topographic

## Known Limitations

- OpenStreetMap geocoding rate limited to 1 request/second
- Some historical addresses may not geocode successfully
- Browser storage not supported (data loads from CSV each time)
- Large datasets (20,000+ events) may have performance issues

## Future Enhancements

Potential improvements for future versions:
- Manual geocoding correction interface
- Export filtered data to new CSV
- Photo/document attachments to events
- Family relationship lines on map
- Heatmap view
- 3D terrain visualization

## Credits

- **Mapbox GL JS**: Map rendering
- **OpenStreetMap Nominatim**: Geocoding service
- **python-gedcom**: GEDCOM parsing
- **geopy**: Geocoding library

## License

This project is provided as-is for personal use. Mapbox and OpenStreetMap have their own usage terms.

## Support

For issues or questions:
1. Check browser console for errors
2. Verify all prerequisites are met
3. Ensure CSV files are properly formatted
4. Check that Mapbox token is valid

---

**Happy Family Tree Mapping! 🌳🗺️**
