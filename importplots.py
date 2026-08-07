import sqlite3
import os
import time
import re
import requests
from google import genai
from google.genai import errors as genai_errors

# GEMINI API KEY
# NOTE: using Gemini for now (free tier); plan to switch to Anthropic later.
with open("gemini_apikey.txt", "r") as f:
    GEMINI_API_KEY = f.read().strip()

client = genai.Client(api_key=GEMINI_API_KEY)
GEMINI_MODEL = "gemini-3.5-flash-lite"

# Free tier for this model allows 15 requests/minute; pace calls to stay under that.
GEMINI_SECONDS_BETWEEN_CALLS = 4.5


class GeminiRateLimitError(Exception):
    """Raised when the Gemini API quota is exhausted, to stop the batch early."""
    pass


def set_up_database():
    """
    Sets up a SQLite database connection and cursor.

    Returns
    -----------------------
    Tuple (Cursor, Connection):
        A tuple containing the database cursor and connection objects.
    """
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/movies.db")
    cur = conn.cursor()
    return cur, conn


def create_plots_table(cur, conn):
    """
    Creates the Plots table in the database if it doesn't exist.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    cur.execute('''
        CREATE TABLE IF NOT EXISTS Plots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER UNIQUE,
            plot_summary TEXT,
            FOREIGN KEY (movie_id) REFERENCES Movies(id)
        )
    ''')
    conn.commit()


def search_wikipedia(movie_title):
    """
    Searches Wikipedia for the article title that best matches a movie.
    Used as a fallback when a direct title lookup doesn't find a page.

    Parameters
    -----------------------
    movie_title: str
        The title of the movie to search for.

    Returns
    -----------------------
    str or None:
        The best matching Wikipedia article title if found, None otherwise.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': movie_title + ' film',
        'format': 'json',
        'srlimit': 5
    }

    try:
        time.sleep(0.1)
        response = requests.get(url, params=params, headers={'User-Agent': 'MovieAccuracyProject/1.0 (gveettil@umich.edu)'})

        if response.status_code == 200:
            search_results = response.json().get('query', {}).get('search', [])
            if search_results:
                best_match = search_results[0]['title']
                print(f"  Found Wikipedia match: {best_match}")
                return best_match
            return None

        print(f"  Wikipedia search returned status {response.status_code} for '{movie_title}': {response.text[:200]}")
        return None
    except Exception as e:
        print(f"  Search error for {movie_title}: {e}")
        return None


def get_wikipedia_article_text(article_title):
    """
    Fetches the full plain-text extract of a Wikipedia article via the
    MediaWiki Action API. Following redirects automatically avoids the need
    to guess the exact canonical title.

    Parameters
    -----------------------
    article_title: str
        The Wikipedia article title to fetch.

    Returns
    -----------------------
    str or None:
        The article's plain text if the page exists, None otherwise.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'prop': 'extracts',
        'explaintext': 1,
        'redirects': 1,
        'titles': article_title,
        'format': 'json',
    }

    try:
        time.sleep(0.1)
        response = requests.get(url, params=params, headers={'User-Agent': 'MovieAccuracyProject/1.0 (gveettil@umich.edu)'})

        if response.status_code != 200:
            print(f"  Wikipedia extract lookup returned status {response.status_code} for '{article_title}': {response.text[:200]}")
            return None

        pages = response.json().get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            if page_id == '-1' or 'missing' in page:
                return None
            return page.get('extract')

        return None
    except Exception as e:
        print(f"  Error fetching article '{article_title}': {e}")
        return None


def extract_wikipedia_article_year(article_text):
    """
    Extracts the release year a Wikipedia film article states about itself,
    from its opening sentence (e.g. "X is a 2006 Hong Kong martial arts
    film..."). Used to verify we fetched the right article when multiple
    unrelated films share an exact title (e.g. two different movies both
    called "Fearless").

    Parameters
    -----------------------
    article_text: str
        The full plain-text Wikipedia article.

    Returns
    -----------------------
    int or None: The stated year, or None if no year could be found in the
        opening of the article.
    """
    opening = article_text[:400]
    match = re.search(r'\bis an?\b.{0,40}?\b(19\d{2}|20\d{2})\b', opening)
    if match:
        return int(match.group(1))

    match = re.search(r'\b(19\d{2}|20\d{2})\b', opening)
    return int(match.group(1)) if match else None


def get_wikipedia_text_for_movie(movie_title, release_year=None):
    """
    Finds the Wikipedia article for a movie and returns its full plain text.
    Tries, in order: the "(<year> film)" disambiguated title (Wikipedia's
    standard convention when multiple films share a title), the top search
    result (qualified with "film"), then a literal direct title lookup.
    When release_year is known, each candidate's stated year is checked
    against it -- this catches cases where an unrelated same-titled film
    would otherwise be silently accepted (e.g. "Fearless" the 1993 plane
    crash drama vs. "Fearless" the 2006 martial arts film).

    Parameters
    -----------------------
    movie_title: str
        The title of the movie.
    release_year: int or None
        The movie's real release year (from TMDB), if known, for
        year-of-release verification.

    Returns
    -----------------------
    str or None:
        The matched article's plain text, or None if no verified article
        was found.
    """
    candidate_titles = []
    if release_year:
        candidate_titles.append(f"{movie_title} ({release_year} film)")

    search_result = search_wikipedia(movie_title)
    if search_result:
        candidate_titles.append(search_result)

    candidate_titles.append(movie_title)

    for candidate_title in candidate_titles:
        text = get_wikipedia_article_text(candidate_title)
        if not text:
            continue

        if release_year is None:
            return text

        found_year = extract_wikipedia_article_year(text)
        if found_year is None or abs(found_year - release_year) <= 1:
            return text

        print(f"  '{candidate_title}' states {found_year}, expected {release_year} -- likely a different film with the same title, trying next candidate")

    print(f"  Wikipedia page not found for: {movie_title}")
    return None


def extract_plot_with_llm(movie_title, article_text):
    """
    Uses an LLM to extract the film's fictional plot/synopsis from raw
    Wikipedia article text, regardless of how the section is headed
    (Plot, Synopsis, Premise, Story, etc.) or where it falls in the page.

    Parameters
    -----------------------
    movie_title: str
        The title of the movie, used to confirm the article matches.
    article_text: str
        The full plain-text Wikipedia article.

    Returns
    -----------------------
    str or None:
        The extracted plot summary, or None if the article doesn't
        actually contain one (wrong page, no plot section, etc.).
    """
    # Film articles keep the plot near the top of the page, so trimming
    # keeps requests fast/cheap without losing the plot section.
    trimmed_text = article_text[:20000]

    # NOTE: the sentinel word is deliberately "UNMATCHED", not "NONE", and the
    # no-match rule deliberately avoids phrases like "wrong page" or
    # "disambiguation page" -- a prior wording reliably tripped Gemini's
    # PROHIBITED_CONTENT safety filter whenever the article had mature
    # content (violence, sexual assault, etc.), silently returning an empty
    # response for every such movie. This phrasing was verified not to
    # trigger the filter across multiple repeated calls on the same article.
    prompt = f"""Below is the full text of a Wikipedia article that should be about the film "{movie_title}".

Extract ONLY the plot/synopsis of the film's fictional story -- the section usually titled "Plot", "Synopsis", "Premise", or similar. Do not include cast lists, production history, reception, or real-world background information.

Return ONLY the plot summary text, with no preamble, headers, or commentary. If the article is not about this film, or has no plot section, respond with just the single word UNMATCHED instead.

Article text:
{trimmed_text}"""

    time.sleep(GEMINI_SECONDS_BETWEEN_CALLS)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
    except genai_errors.APIError as e:
        if e.code == 429:
            raise GeminiRateLimitError(str(e))
        print(f"  Gemini API error for '{movie_title}': {e}")
        return None

    if response.text is None:
        block_reason = getattr(response.prompt_feedback, 'block_reason', None) if response.prompt_feedback else None
        print(f"  Gemini returned no content for '{movie_title}' (block_reason: {block_reason})")
        return None

    result = response.text.strip()
    if not result or result == "UNMATCHED":
        return None
    return result


def populate_plots_table(cur, conn, limit=25):
    """
    Populates the Plots table with plot summaries extracted via an LLM.
    Processes movies that don't have plots yet OR have NULL plot summaries.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    limit: int
        Maximum number of plots to fetch per run (default 25).
    """
    cur.execute('''
        SELECT m.id, m.title, CAST(substr(rd.date, 1, 4) AS INTEGER) as release_year
        FROM Movies m
        LEFT JOIN MovieReleaseDates mrd ON m.id = mrd.movie_id
        LEFT JOIN ReleaseDates rd ON mrd.release_date_id = rd.id
        WHERE m.id NOT IN (SELECT movie_id FROM Plots WHERE plot_summary IS NOT NULL)
        LIMIT ?
    ''', (limit,))

    movies_to_process = cur.fetchall()

    if not movies_to_process:
        print("All movies already have plots stored!")
        return

    print(f"Processing {len(movies_to_process)} movies...")

    successful = 0
    for movie_id, title, release_year in movies_to_process:
        print(f"Fetching plot for: {title}")
        article_text = get_wikipedia_text_for_movie(title, release_year)

        plot = None
        if article_text:
            try:
                plot = extract_plot_with_llm(title, article_text)
            except GeminiRateLimitError as e:
                print(f"\nGemini rate limit hit, stopping this run early: {e}")
                break

        if plot:
            cur.execute('''
                INSERT OR REPLACE INTO Plots (movie_id, plot_summary)
                VALUES (?, ?)
            ''', (movie_id, plot))
            successful += 1
        else:
            # Store NULL to mark that we tried but couldn't find a plot
            cur.execute('''
                INSERT OR REPLACE INTO Plots (movie_id, plot_summary)
                VALUES (?, NULL)
            ''', (movie_id,))

    conn.commit()
    print(f"\nSuccessfully stored {successful} plots out of {len(movies_to_process)} movies.")

    cur.execute('SELECT COUNT(*) FROM Plots WHERE plot_summary IS NOT NULL')
    total_processed = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Movies')
    total_movies = cur.fetchone()[0]
    print(f"Total progress: {total_processed}/{total_movies} movies have plots.")


def main():
    cur, conn = set_up_database()
    create_plots_table(cur, conn)
    populate_plots_table(cur, conn, limit=25)

    conn.close()


if __name__ == "__main__":
    main()
