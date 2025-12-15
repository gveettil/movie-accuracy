# True Story Movie Analysis Project

## Project Overview

This project analyzes movies based on true stories using data from The Movie Database (TMDB) API. It collects movie data, categorizes movies by subject type, and generates visualizations and statistics about true story movies.

The project uses a **normalized database design** to eliminate duplicate string data and follows proper database design principles.

---

## Database Structure

The project creates a SQLite database (`movies.db`) with the following **normalized** tables:

### Core Tables:
1. **Movies** (~250 rows) - Stores core movie information
   - id, title, tmdb_id, release_date (kept for backwards compatibility), revenue, overview

2. **Genres** (~20 rows) - Stores unique genre names (no duplicates!)
   - id, name

3. **MovieGenres** (~500+ rows) - Junction table for many-to-many relationship
   - id, movie_id, genre_id

4. **Categories** (~10 rows) - Stores unique category names (no duplicates!)
   - id, name

5. **MovieCategories** (~250 rows) - Junction table linking movies to categories
   - id, movie_id, category_id

6. **ReleaseDates** (~100-150 rows) - Stores unique release dates (no duplicates!)
   - id, date

7. **MovieReleaseDates** (~250 rows) - Junction table linking movies to release dates
   - id, movie_id, release_date_id

**Key Design Features:**
- All data comes from TMDB API (single source)
- No duplicate string data (genres, categories, and release dates stored once, referenced via foreign keys)
- Tables have different row counts (proper normalization)
- All data for one entity (movie) is in Movies table, not split across tables
- Foreign keys enforce referential integrity
- Genres, categories, AND release dates all use the same normalized pattern (lookup table + junction table)

---

## Files and Order of Execution

### 1. `importmovielist.py` - IMDb Movie List Scraper
**Purpose:** Scrapes IMDb for a list of ~250 true story movies and populates movie titles into the database.

**What it does:**
- Uses Selenium to scrape https://www.imdb.com/list/ls021398170/
- Handles infinite scroll to load movies
- Creates Movies table with title field
- Processes 25 movies per run (buffered batches)
- Tracks progress and resumes from where it left off

**How many times to run:** MULTIPLE TIMES (10+ times to import all ~250 movies)
- Processes 25 movies per run
- Run until you see: "All movies have already been imported!"

**Command:** `python importmovielist.py`

---

### 2. `tmdbdata.py` - TMDB Data Fetcher
**Purpose:** Fetches detailed movie data from TMDB API for movies in the database and creates normalized genre and release date structures.

**What it does:**
- Searches TMDB for each movie title
- Creates Genres and MovieGenres tables (normalized many-to-many structure)
- Creates ReleaseDates and MovieReleaseDates tables (normalized many-to-many structure)
- Updates Movies table with: tmdb_id, release_date, revenue, overview
- Normalizes genre data (NO duplicate genre strings!)
- Normalizes release date data (NO duplicate date strings!)
- Processes 25 movies per run (API rate limiting)

**How many times to run:** MULTIPLE TIMES (10+ times to fetch data for all ~250 movies)
- Processes 25 movies per run
- Run until you see: "All movies already have TMDB data!"

**Command:** `python tmdbdata.py`

---

### 3. `moviecalc.py` - Categorization and Calculations
**Purpose:** Categorizes movies by subject type and performs statistical calculations.

**What it does:**
- Creates the Subject_Categories table
- Categorizes movies into subject types based on TMDB overview:
  - Musicians, Athletes, Criminals, Military, Businesspeople
  - Scientists, Activists, Politicians, Artists & Writers, Entertainers
  - Historical Events, Other
- Processes 25 movies per run
- Generates calculations and writes to `calculations_output.txt`:
  - Count of movies by category
  - Most common genres by category (uses JOIN with Genres table)
  - Average revenue by category
  - Revenue trends by release year

**How many times to run:** MULTIPLE TIMES (10+ times to categorize all movies)
- Processes 25 movies per run
- Run until you see: "All movies have been categorized!"
- The calculations output is updated each run

**Command:** `python moviecalc.py`

---

### 4. `visualizations.py` - Data Visualizations
**Purpose:** Creates visual charts and graphs from the analyzed data.

**What it does:**
- Creates 4 visualizations:
  1. Bar chart: Movie count by subject category
  2. Stacked bar chart: Genre distribution by subject category (uses normalized tables)
  3. Bar chart: Average revenue by subject category
  4. Line plot: Average revenue by release year

**Output files:**
- `visualization_1_category_counts.png`
- `visualization_2_genre_by_category.png`
- `visualization_3_avg_revenue.png`
- `visualization_4_revenue_by_year.png`

**How many times to run:** ONCE (after all data is collected and calculations made)
- Run after completing all data collection steps
- Can be re-run anytime to regenerate visualizations

**Command:** `python visualizations.py`

---

## Complete Workflow

Follow this order to run the project from scratch:

```bash
# Step 1: Scrape IMDb for movie titles (run 10+ times until complete)
python importmovielist.py
python importmovielist.py
# ... repeat until all ~250 movies are imported

# Step 2: Fetch TMDB data for those movies (run 10+ times until complete)
python tmdbdata.py
python tmdbdata.py
# ... repeat until all movies have TMDB data

# Step 3: Categorize and calculate (run 10+ times until complete)
python moviecalc.py
python moviecalc.py
# ... repeat until all movies are categorized

# Step 4: Generate visualizations (run ONCE)
python visualizations.py
```

---

## Output Files

- `movies.db`: SQLite database containing all movie data in normalized schema
- `calculations_output.txt`: Statistical analysis results
- `visualization_1_category_counts.png`: Category distribution chart
- `visualization_2_genre_by_category.png`: Genre analysis chart
- `visualization_3_avg_revenue.png`: Revenue by category chart
- `visualization_4_revenue_by_year.png`: Revenue trends over time

---