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

8. **Plots** (~250 rows) - Stores each movie's fictional plot summary, extracted from Wikipedia via an LLM
   - id, movie_id (UNIQUE), plot_summary

9. **RealSubjects** (~150-200 rows) - Stores unique real-world people/events/places that movies are based on (no duplicates!)
   - id, wikipedia_title (UNIQUE), subject_type (Person/Event/Place), summary

10. **MovieRealSubjects** (~200-250 rows) - Junction table linking movies to real-world subjects (many-to-many, like MovieGenres)
    - id, movie_id, subject_id (nullable — NULL marks "checked, nothing found")

11. **TruthScores** (~210 rows) - Stores each movie's computed "Truth Index" (0-100) and its rubric sub-scores
    - id, movie_id (UNIQUE), people_score, events_score, outcome_score, timeline_score, consensus_score, truth_index, explanation

**Key Design Features:**
- All data comes from TMDB API (single source)
- No duplicate string data (genres, categories, and release dates stored once, referenced via foreign keys)
- Tables have different row counts (proper normalization)
- All data for one entity (movie) is in Movies table, not split across tables
- Foreign keys enforce referential integrity
- Genres, categories, AND release dates all use the same normalized pattern (lookup table + junction table)

---

## Files and Order of Execution

**Note on LLM provider:** `importplots.py`, `importrealevents.py`, and `truthscore.py` currently call the Gemini API (free tier). Their LLM-calling functions are named provider-neutral (e.g. `extract_plot_with_llm`, not `..._with_gemini`) specifically so the provider can be swapped later — once an Anthropic API key is available, dropping in the Claude API is meant to be a small, contained change (swap the `google-genai` client/calls for `anthropic.Anthropic().messages.create(...)` in each script, update `requirements.txt`), not a rewrite.

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

### 4. `importplots.py` - Fictional Plot Extraction
**Purpose:** Fetches each movie's fictional plot from Wikipedia and extracts it with an LLM (Gemini).

**What it does:**
- Finds each movie's Wikipedia article (trying, in order: the `"<title> (<year> film)"` disambiguated title, a `"<title> film"` search, then a literal title lookup), cross-checking the article's own stated release year against TMDB's release year to catch cases where an unrelated film shares an exact title (e.g. two different movies both called "Fearless")
- Sends the full article text to Gemini and asks it to extract just the fictional plot/synopsis section, regardless of whether Wikipedia labels it "Plot," "Synopsis," or "Premise"
- Creates the `Plots` table
- Processes 25 movies per run

**How many times to run:** MULTIPLE TIMES (10+ times)
- Run until you see: "All movies already have plots stored!"
- A handful of movies never get a plot (Wikipedia article has no plot section, or Gemini's safety filter blocks mature-content articles) — this is expected, not a bug

**Command:** `python importplots.py`

---

### 5. `importrealevents.py` - Real-World Subject Identification
**Purpose:** Identifies the real person, event, or place each movie is based on (separately from the film's own Wikipedia article used above), and summarizes it.

**What it does:**
- Asks Gemini to identify up to 3 real-world subjects from each movie's TMDB overview — but only when the overview gives a specific, identifying detail (a name, a named event); a vague overview correctly yields no subjects rather than a guessed answer
- Searches Wikipedia for each subject and has Gemini pick the correct article from real candidate summaries (not misleading search snippets)
- Summarizes the correct article and stores it, creating the `RealSubjects` and `MovieRealSubjects` tables
- Processes 25 movies per run

**How many times to run:** MULTIPLE TIMES (10+ times)
- Run until you see: "All movies have already been processed for real-world subjects!"

**Command:** `python importrealevents.py`

---

### 6. `truthscore.py` - Truth Index Scoring
**Purpose:** Computes a 0–100 "Truth Index" for each movie by comparing its fictional plot against its real-world subject(s).

**What it does:**
- For each movie with both a plot and a resolved real subject, asks Gemini to rate 4 fixed criteria (people, events, outcome, timeline) each 0–2, based only on data already in the database
- Combines those into a single 0–100 score via a fixed, deterministic formula (not LLM-generated): `round((people + events + outcome + timeline) / 8 * 100)`
- Also attempts a 5th "consensus" criterion via live Google Search grounding (weighted at half the others) — **confirmed unavailable on Gemini's free tier**, so this currently always falls back to the 4-criteria formula above
- Creates the `TruthScores` table
- Processes 25 movies per run

**How many times to run:** MULTIPLE TIMES (10+ times)
- Run until you see: "All eligible movies already have truth scores!"
- Not every movie is eligible — see **Known Limitations** below

**Command:** `python truthscore.py`

---

### 7. `visualizations.py` - Data Visualizations
**Purpose:** Creates visual charts and graphs from the analyzed data.

**What it does:**
- Creates 6 visualizations:
  1. Bar chart: Movie count by subject category
  2. Stacked bar chart: Genre distribution by subject category (uses normalized tables)
  3. Bar chart: Average revenue by subject category
  4. Line plot: Average revenue by release year
  5. Bar chart: Distribution of Truth Index scores across all scored movies
  6. Bar chart: Average Truth Index by subject category

**Output files:**
- `visualization_1_category_counts.png`
- `visualization_2_genre_by_category.png`
- `visualization_3_avg_revenue.png`
- `visualization_4_revenue_by_year.png`
- `visualization_5_truth_index_distribution.png`
- `visualization_6_truth_index_by_category.png`

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

# Step 4: Extract fictional plots (run 10+ times until complete)
python importplots.py
python importplots.py
# ... repeat until all movies have plots

# Step 5: Identify real-world subjects (run 10+ times until complete)
python importrealevents.py
python importrealevents.py
# ... repeat until all movies are processed

# Step 6: Compute Truth Index scores (run 10+ times until complete)
python truthscore.py
python truthscore.py
# ... repeat until all eligible movies are scored

# Step 7: Generate visualizations (run ONCE)
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
- `visualization_5_truth_index_distribution.png`: Truth Index distribution chart
- `visualization_6_truth_index_by_category.png`: Truth Index by category chart

---

## Known Limitations

**Not every movie gets a Truth Index score.** Scoring requires both a fictional plot (from `importplots.py`) and at least one resolved real-world subject (from `importrealevents.py`). Some movies never get either — a Wikipedia article with no plot section, or Gemini's safety filter blocking a mature-content article (e.g. articles involving war violence or sexual assault) — and this is expected, not a bug.

**A small number of movies (22) had to be manually excluded from scoring.** During testing, some movies' underlying TMDB data turned out to describe a *different, unrelated movie* that happens to share the exact title (e.g. our stored data for `"Elizabeth"` was for an unrelated film, not the 1998 Cate Blanchett biopic; `"Detroit"` was an unrelated German road-trip film, not the 2017 film about the 1967 riots). This is a bug in `tmdbdata.py`, which accepts TMDB's top search result with no verification — the same class of issue that `importplots.py`'s Wikipedia lookup was fixed to catch (see below), except here it happens at the very first data-collection stage, before any of the later scripts even run.

Fixing `tmdbdata.py` itself was out of scope for this pass (it would require re-verifying and re-fetching TMDB data, then cascading re-runs through categorization, plot extraction, real-subject identification, and scoring). Instead, the 22 affected movies were **manually excluded directly in the database** — their real-subject links were removed so `truthscore.py` skips them, rather than presenting a confidently-wrong Truth Index as a real finding. **This exclusion is a one-time manual fix, not something any script does** — if `movies.db` were rebuilt from scratch, these same movies would need to be found and excluded again by hand, since nothing in the pipeline code currently prevents or detects this class of bug. A proper fix would add the same kind of verification `importplots.py` now does for Wikipedia (cross-checking a candidate's stated release year against the movie's real year before accepting it) to `tmdbdata.py`'s TMDB search step.

**Wikipedia title collisions were a real, separate bug that *is* now fixed.** Before this fix, roughly 10% of scored movies were built on the *wrong film's plot* because their exact title is shared by a completely different movie (e.g. two different films both called `Fearless`, `Belle`, or `Chocolat`). `importplots.py` now cross-checks each candidate Wikipedia article's stated release year against the movie's real TMDB release year before accepting it, which is a durable, reproducible part of the pipeline — this one does not require manual reapplication.

---