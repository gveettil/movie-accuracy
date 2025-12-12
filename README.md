# Movie Accuracy Project

## Project Overview

This project analyzes movies based on true stories from IMDb. It collects movie data from multiple sources (IMDb, Wikipedia, and TMDB), categorizes movies by subject type, and generates visualizations and statistics about true story movies.

The project uses web scraping, API calls, and a SQLite database to store and analyze data about 250+ movies based on true events.

---

## Database Structure

The project creates a SQLite database (`movies.db`) with the following tables:
- Movies: Stores movie titles
- Plots: Stores Wikipedia plot summaries
- TMDB_Data: Stores TMDB data (genres, release dates, revenue)
- Subject_Categories: Categorizes movies by subject type (Musicians, Athletes, Criminals, etc.)

---

## Files and Order of Execution 

### 1. `importmovielist.py` - Movie List Import
Purpose: Scrapes IMDb to get a list of 250 movies based on true stories and populates the Movies table.

What it does:
- Uses Selenium to scrape IMDb's "Movies Based on True Stories" list
- Handles infinite scroll to load all 250 movies
- Creates the Movies table in the database
- Inserts movie titles into the database

*How many times to run: ONCE (at the very beginning)
- This initializes your database with the movie list
- Running it again won't duplicate entries (uses INSERT OR IGNORE)

Command: `python importmovielist.py`

---

### 2. `importplots.py` - Wikipedia Plot Import
Purpose: Fetches plot summaries from Wikipedia for movies in the database.

What it does:
- Creates the Plots table
- Searches Wikipedia for each movie's plot summary
- Processes 25 movies per run (API rate limiting)
- Stores plot summaries or NULL if not found

How many times to run: MULTIPLE TIMES (10+ times to process all 250 movies)
- Processes 25 movies per run
- For 250 movies: 250 ÷ 25 = 10 runs minimum (Run as many many times as number of items in movie list / 25)
- Run until you see: "All movies already have plots stored!"

Command: `python importplots.py`

---

### 3. `tmdbdata.py` - TMDB Data Import
Purpose: Fetches movie metadata (genres, release dates, revenue) from The Movie Database (TMDB) API.

What it does:
- Creates the TMDB_Data table
- Searches TMDB for each movie
- Retrieves genres, release dates, and box office revenue
- Processes 25 movies per run (API rate limiting)

Requirements: You need a TMDB API key stored in `tmdb_apikey.txt`

How many times to run: MULTIPLE TIMES (10+ times to process all 250 movies)
- Processes 25 movies per run
- For 250 movies: 250 ÷ 25 = 10 runs minimum (Run as many many times as number of items in movie list / 25)
- Run until all movies are processed

Command: `python tmdbdata.py`

---

### 4. `moviecalc.py` - Categorization and Calculations
Purpose: Categorizes movies by subject type and performs statistical calculations.

What it does**:
- Creates the Subject_Categories table
- Categorizes movies into subject types:
  - Musicians, Athletes, Criminals, Military, Businesspeople
  - Scientists, Activists, Politicians, Artists & Writers, Entertainers
  - Historical Events, Other
- Processes 25 movies per run
- Generates calculations and writes to `calculations_output.txt`:
  - Count of movies by category
  - Most common genres by category
  - Average revenue by category
  - Revenue trends by release year

*How many times to run: MULTIPLE TIMES (10+ times to categorize all movies)
- Processes 25 movies per run
- For 250 movies: 250 ÷ 25 = 10 runs minimum (Run as many many times as number of items in movie list / 25)
- Run until you see: "All movies have been categorized!"
- The calculations output is updated each run

Command*: `python moviecalc.py`

---

### 5. `visualizations.py` - Data Visualizations
purpose: Creates visual charts and graphs from the analyzed data.

What it does:
- Creates 4 visualizations:
  1. Bar chart: Movie count by subject category
  2. Stacked bar chart: Genre distribution by subject category
  3. Bar chart: Average revenue by subject category
  4. Line plot: Average revenue by release year

Output files:
- `visualization_1_category_counts.png`
- `visualization_2_genre_by_category.png`
- `visualization_3_avg_revenue.png`
- `visualization_4_revenue_by_year.png`

How many times to run: ONCE (after all data is collected and calculations made)
- Run after completing all data collection steps and new data created/calculated
- Can be re-run anytime to regenerate visualizations

Command: `python visualizations.py`

---

## Complete Workflow

Follow this order to run the project from scratch:

```bash
# Step 1: Import movie list (run ONCE)
python importmovielist.py

# Step 2: Import plots (run 10+ times until complete)
python importplots.py
python importplots.py
# ... repeat until all movies have plots

# Step 3: Import TMDB data (run 10+ times until complete)
python tmdbdata.py
python tmdbdata.py
# ... repeat until all movies are processed

# Step 4: Categorize and calculate (run 10+ times until complete)
python moviecalc.py
python moviecalc.py
# ... repeat until all movies are categorized

# Step 5: Generate visualizations (run ONCE)
python visualizations.py
```

---

## Output Files

- `movies.db`: SQLite database containing all movie data
- `calculations_output.txt`: Statistical analysis results
- `visualization_1_category_counts.png`: Category distribution chart
- `visualization_2_genre_by_category.png`: Genre analysis chart
- `visualization_3_avg_revenue.png`: Revenue by category chart
- `visualization_4_revenue_by_year.png`: Revenue trends over time

---
