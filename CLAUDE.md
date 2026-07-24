# Project context for AI agents

SI 201 final project: analyzes ~250 "based on a true story" movies (IMDb list → TMDB data → subject categorization → visualizations). See [README.md](README.md) for the documented pipeline and database structure overview.

## Database must stay normalized

`movies.db` is intentionally normalized (3NF) as a course requirement — do not "simplify" this by flattening lookup tables back into `Movies`, even where it looks redundant.

- `Genres`, `Categories`, `ReleaseDates` are all lookup tables (unique `name`/`date`) joined to `Movies` through junction tables (`MovieGenres`, `MovieCategories`, `MovieReleaseDates`), each with a `UNIQUE(movie_id, x_id)` constraint. No genre/category/date string is ever duplicated — always insert-or-get into the lookup table, then link via the junction table.
- `Plots` is the one genuine 1:1 table: `movie_id` is directly `UNIQUE` with no junction table, because there's no multiplicity to model (one plot per movie).
- `Categories` and `ReleaseDates` are modeled as many-to-many (junction tables) even though, in the current data, every movie has exactly one of each — verified via `GROUP BY movie_id HAVING COUNT(*) > 1` returning zero rows for both. That's intentional schema consistency with the genuinely many-to-many `Genres` table, not a bug — don't "fix" it by collapsing them into single columns on `Movies`.
- Keep using the `insert_or_get_x(cur, conn, name)` pattern (see `tmdbdata.py`, `moviecalc.py`) for any new lookup-table data: check for existing row by unique value, insert only if missing, return the id.

## Batch-processing pattern (course requirement: ≤25 API calls/run)

`importmovielist.py`, `tmdbdata.py`, `moviecalc.py`, and `importplots.py` all process at most 25 rows per run and are meant to be re-run repeatedly until they print an "All X already have Y!" completion message. Any new data-fetching script should follow this same pattern (query for unprocessed rows `LIMIT 25`, process, commit, print progress).

## `importplots.py` specifics

- Fetches each movie's fictional plot from Wikipedia and extracts it via an LLM (handles inconsistent "Plot"/"Synopsis"/"Premise" section naming that broke the original BeautifulSoup heading-search approach).
- **Wikipedia lookup order matters**: `get_wikipedia_text_for_movie()` calls `search_wikipedia()` (which appends `" film"` to the query) *before* trying a literal direct-title lookup. This was a real bug fix — literal lookups on short/common titles (`42`, `300`, `Ali`, `Attila`, `Admiral`, `Agora`) resolve to unrelated, more prominent Wikipedia articles (a number, a year, a historical figure, a naval rank, an ancient marketplace) instead of the film. Don't revert this order.
- Wikipedia API calls use a `User-Agent` with contact info (`MovieAccuracyProject/1.0 (gveettil@umich.edu)`) — generic UAs get throttled harder under Wikipedia's User-Agent policy. Both `search_wikipedia()` and `get_wikipedia_article_text()` print the HTTP status + response snippet on any non-200 response — keep this; a previous silent-failure version made an entire batch look like "no Wikipedia page found" when it was actually a swallowed rate-limit error, and was very hard to diagnose.
- **LLM provider is currently Gemini**, not Anthropic — reads `gemini_apikey.txt`, uses `google-genai` SDK. This is temporary: user has free Gemini quota now and plans to switch to the Anthropic API later. The extraction function is deliberately named `extract_plot_with_llm` (not `..._with_claude` or `..._with_gemini`) so the provider can be swapped without a rename. `anthropic_apikey.txt` already exists as a placeholder for that future switch — when asked to switch, swap the `google.genai` client/call for `anthropic.Anthropic().messages.create(...)`, update `requirements.txt` (`google-genai` → `anthropic`), keep everything else (prompt, DB writes, Wikipedia fetch logic) unchanged.
- Gemini's free tier caps `gemini-3.5-flash-lite` at 15 requests/minute. The code paces calls with `GEMINI_SECONDS_BETWEEN_CALLS = 4.5` and raises `GeminiRateLimitError` on a 429, which `populate_plots_table()` catches to `break` out of the batch loop early (rather than letting the exception propagate and crash `main()`).
- **Commit-once-per-batch caveat**: `populate_plots_table()` calls `conn.commit()` once, after the whole loop — not per-row. An uncaught exception mid-loop loses every plot fetched earlier in that run (this is why an uncaught 429 previously wiped a whole batch, and why the rate-limit handling specifically uses `break` rather than raising further — `break` still reaches the trailing `conn.commit()`). If adding new failure modes to this loop, make sure they're either caught-and-`break` (to preserve partial progress) or genuinely fatal.

## Original project vision (context for future scope)

Before pivoting to the current scope, the goal was a "truth index": extract a movie's fictional plot (now underway in `importplots.py`), separately find and summarize the real event/person/place Wikipedia article(s) the movie is based on, then use an LLM to score factual accuracy between the two. The real-event lookup is the hard unsolved part (a movie can map to multiple real subjects — person + event + place — and naive title search won't resolve it the way it does for the film's own article). If asked to build this next, the disambiguation problem is the main design challenge, not the summarization or scoring steps.

## Repo hygiene notes

- `venv/` is the project's virtualenv, dependencies tracked in `requirements.txt`, install via `./venv/bin/pip install -r requirements.txt`.
- All `*_apikey.txt` files are gitignored. **Exception**: `tmdb_apikey.txt` was committed to git before `.gitignore` existed and is still tracked — it should be rotated and untracked at some point, but that cleanup hasn't been done yet.
