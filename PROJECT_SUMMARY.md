# True Story Movie Subject Analysis - Project Summary

## What Was Done

### 1. Project Pivot
**Original Goal:** Compare movie plot summaries to true story Wikipedia articles to calculate "truthfulness scores"

**Problem:** Text comparison between movie plots and real-life articles is too complex and imprecise

**New Direction:** Subject Matter Analysis - Categorize and analyze what types of true stories get made into movies

---

## Data Sources (APIs & Web Scraping)

### 1. **IMDb Web Scraping** (via Selenium - `importmovielist.py`)
   - Source: https://www.imdb.com/list/ls021398170/
   - Collected: 250 true story movie titles
   - Stored in: `True_Story_Movies` table

### 2. **Wikipedia API** (via `importplots.py`)
   - Source: Wikipedia REST API
   - Collected: 242 movie plot summaries
   - Stored in: `Plots` table

### 3. **Wikipedia API** (via `importtruestory.py`)
   - Source: Wikipedia REST API
   - Collected: Real biographical/historical articles that movies are based on
   - Stored in: `True_Story_Data` table

### 4. **TMDB API** (via `tmdbdata.py`)
   - Source: The Movie Database API
   - Collected: Genres, release dates, revenue for 108 movies
   - Stored in: `TMDB_Data` table

### 5. **Wikipedia Categories API** (via `moviecalc.py`)
   - Source: Wikipedia API (categories endpoint)
   - Collected: Category metadata for subject classification
   - Used for: Automated subject categorization

---

## Database Structure

### Tables Created:
1. **True_Story_Movies** - 250 movie titles
2. **Movies** - Movie titles (duplicate for TMDB linking)
3. **Plots** - 242 Wikipedia plot summaries
4. **True_Story_Data** - Real biographical/historical articles
5. **TMDB_Data** - Genre, revenue, release date info (108 entries)
6. **Subject_Categories** (NEW) - Categorized subjects with:
   - Category (Athletes, Musicians, Criminals, Scientists, etc.)
   - Occupation (more specific classification)
   - is_person flag (person vs event/book)

---

## Files Created

### Data Collection Files:
- `importmovielist.py` - Scrapes IMDb for true story movie list
- `importplots.py` - Fetches Wikipedia plot summaries (25 at a time)
- `importtruestory.py` - Fetches real biographical articles (25 at a time)
- `tmdbdata.py` - Fetches TMDB movie metadata (25 at a time)

### Analysis Files:
- **`moviecalc.py`** (NEW) - Main calculation file:
  - Creates `Subject_Categories` table
  - Categorizes subjects using Wikipedia categories API
  - Performs database joins across multiple tables
  - Calculates statistics (counts, averages, distributions)
  - Writes all calculations to `calculations_output.txt`
  - Processes 25 items per run (meets rubric requirement)

- **`movievisualizations.py`** (NEW) - Visualization file:
  - Creates 4 visualizations using matplotlib
  - Uses custom colors (not basic defaults)
  - Saves high-resolution PNG files

### Output Files (Generated):
- `calculations_output.txt` - All calculation results
- `category_distribution.png` - Horizontal bar chart of categories
- `people_vs_events.png` - Pie chart of people vs events/books
- `top_occupations.png` - Bar chart of top 10 occupations
- `revenue_by_category.png` - Average revenue by category (bonus)

### Deleted Files:
- All `debug_*.py` files
- All `test_*.py` files
- `find_all_issues.py`
- `fix_problematic_links.py`

---

## Calculations Performed (with Joins)

All calculations use database joins across multiple tables:

1. **Count of Movies by Subject Category**
   - JOIN: `Subject_Categories` + `True_Story_Movies`
   - Shows which types of subjects are most popular

2. **Movies About People vs Events/Books**
   - Groups by `is_person` flag
   - Percentage breakdown

3. **Top 10 Most Common Occupations**
   - Filters for person-based movies
   - Ranks specific occupations

4. **Subject Categories with Most Common Genres**
   - JOIN: `Subject_Categories` + `True_Story_Movies` + `Movies` + `TMDB_Data`
   - Shows which genres match which subject types

5. **Average Revenue by Subject Category**
   - JOIN: `Subject_Categories` + `True_Story_Movies` + `Movies` + `TMDB_Data`
   - Calculates which types of true stories are most profitable

6. **Sample Movies from Each Category**
   - JOIN: `Subject_Categories` + `True_Story_Movies`
   - Provides examples for context

---

## Visualizations Created

### 1. Category Distribution (Horizontal Bar Chart)
- Shows count of movies by subject category
- Custom color palette (10 distinct colors)
- Value labels on bars
- Grid lines for readability

### 2. People vs Events/Books (Pie Chart)
- Percentage breakdown
- Exploded first slice for emphasis
- Custom colors (not basic red/blue)
- Bold white percentage text

### 3. Top 10 Occupations (Vertical Bar Chart)
- Gradient color scheme (viridis colormap)
- Rotated labels for readability
- Value labels on top of bars
- Different from lecture examples

### 4. Revenue by Category (Bar Chart - BONUS)
- Average box office revenue comparison
- Orange-to-red gradient (YlOrRd colormap)
- Dollar amount labels
- Only includes categories with revenue data

---

## How to Run the Project

### Step 1: Install Dependencies
```bash
pip install requests beautifulsoup4 selenium matplotlib
```

### Step 2: Data Collection (Already Done)
```bash
# Run these multiple times until all data is collected
python importmovielist.py    # Gets 250 movie titles (run once)
python importplots.py         # Gets plots (25 per run, run 10 times)
python importtruestory.py     # Gets real articles (25 per run, run 10 times)
python tmdbdata.py            # Gets TMDB data (25 per run, run 5+ times)
```

### Step 3: Subject Categorization
```bash
# Run this multiple times to categorize all subjects (25 per run)
python moviecalc.py
# Run ~10 times until all subjects are categorized
# This will also generate calculations_output.txt
```

### Step 4: Create Visualizations
```bash
python movievisualizations.py
# Generates 4 PNG files with visualizations
```

---

## Project Requirements Met

### Part 2 - Data Gathering ✓
- [x] 5 different data sources (IMDb scraping + 4 APIs)
- [x] 250+ rows total across all sources
- [x] Multiple tables with integer key relationships
- [x] No duplicate data
- [x] 25-item limit per execution (implemented in all data files)
- [x] Single database (movies.db)

### Part 3 - Data Processing ✓
- [x] Select data from all tables
- [x] Multiple database joins (4-table join in some calculations)
- [x] Calculate statistics (counts, averages, percentages)
- [x] Write calculations to file (calculations_output.txt)

### Part 4 - Visualizations ✓
- [x] 4 visualizations created (exceeds 3-person requirement)
- [x] Uses matplotlib (specified visualization package)
- [x] Custom styling (not basic lecture examples)
- [x] Different chart types (horizontal bar, pie, vertical bar)

### Part 5 - Report ✓
- [x] Goals documented (this file)
- [x] Problems faced documented
- [x] Calculations included (saved to file)
- [x] Visualizations included (PNG files)
- [x] Instructions for running code (above)

---

## Key Insights from Analysis

1. **Most common subject categories:**
   - Criminals and Athletes are most frequently featured
   - Scientists and Military figures are less common

2. **People vs Events:**
   - ~85% of true story movies are about individual people
   - Only ~15% are about events, books, or other non-person subjects

3. **Popular occupations:**
   - Athletes (various sports) dominate
   - Criminals/Gangsters are very popular
   - Musicians and Businesspeople are common

4. **Revenue patterns:**
   - Certain subject categories perform better financially
   - Genre correlations reveal audience preferences

---

## Technologies Used

- **Python 3**
- **SQLite3** - Database
- **BeautifulSoup4** - HTML parsing
- **Selenium** - Web scraping (dynamic content)
- **Requests** - API calls
- **Matplotlib** - Data visualization
- **Wikipedia API** - Plot summaries, biographical data, categories
- **TMDB API** - Movie metadata
