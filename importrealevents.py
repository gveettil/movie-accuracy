import sqlite3
import os
import time
import re
import json
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


def create_real_subjects_tables(cur, conn):
    """
    Creates the normalized RealSubjects tables:
    - RealSubjects: unique real-world subjects (person/event/place) that
      movies are based on
    - MovieRealSubjects: junction table linking movies to real subjects
      (many-to-many, like MovieGenres)

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    cur.execute('''
        CREATE TABLE IF NOT EXISTS RealSubjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wikipedia_title TEXT UNIQUE NOT NULL,
            subject_type TEXT NOT NULL,
            summary TEXT
        )
    ''')

    # subject_id is nullable so a movie with no identifiable real-world
    # subject can still get a row here (subject_id = NULL), marking it as
    # "checked, nothing found" -- mirrors how Plots stores NULL for movies
    # with no plot, so populate_real_subjects_table() doesn't retry it
    # every run.
    cur.execute('''
        CREATE TABLE IF NOT EXISTS MovieRealSubjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            subject_id INTEGER,
            FOREIGN KEY (movie_id) REFERENCES Movies(id),
            FOREIGN KEY (subject_id) REFERENCES RealSubjects(id),
            UNIQUE(movie_id, subject_id)
        )
    ''')
    conn.commit()


def insert_or_get_real_subject(cur, conn, wikipedia_title, subject_type, summary):
    """
    Inserts a real-world subject into RealSubjects if it doesn't exist,
    and returns its ID. Ensures no duplicate subject rows even if the same
    real person/event/place ends up referenced by multiple movies.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    wikipedia_title: str
        The canonical Wikipedia article title for this subject.
    subject_type: str
        'Person', 'Event', or 'Place'.
    summary: str
        LLM-generated factual summary of the subject.

    Returns
    -----------------------
    int: The subject's ID
    """
    cur.execute("SELECT id FROM RealSubjects WHERE wikipedia_title = ?", (wikipedia_title,))
    result = cur.fetchone()

    if result:
        return result[0]

    cur.execute('''
        INSERT INTO RealSubjects (wikipedia_title, subject_type, summary)
        VALUES (?, ?, ?)
    ''', (wikipedia_title, subject_type, summary))
    conn.commit()
    return cur.lastrowid


def get_wikipedia_article_intro(article_title):
    """
    Fetches just the lead-section plain text of a Wikipedia article. This is
    a more reliable disambiguation signal than a search-result snippet,
    which is an arbitrary highlighted fragment from anywhere in the article
    (e.g. a footnote citation) and can be actively misleading.

    Parameters
    -----------------------
    article_title: str
        The Wikipedia article title to fetch.

    Returns
    -----------------------
    str: The article's lead-section text, or an empty string on failure.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'prop': 'extracts',
        'exintro': 1,
        'explaintext': 1,
        'redirects': 1,
        'titles': article_title,
        'format': 'json',
    }

    try:
        time.sleep(0.1)
        response = requests.get(url, params=params, headers={'User-Agent': 'MovieAccuracyProject/1.0 (gveettil@umich.edu)'})

        if response.status_code != 200:
            return ''

        pages = response.json().get('query', {}).get('pages', {})
        for page_id, page in pages.items():
            if page_id == '-1' or 'missing' in page:
                return ''
            return (page.get('extract') or '')[:400]

        return ''
    except Exception:
        return ''


def search_wikipedia_candidates(subject_name, limit=5):
    """
    Searches Wikipedia for articles matching a real-world subject name and
    returns multiple candidates (title + a real lead-paragraph excerpt), so
    an LLM can pick the correct one instead of blindly trusting the top
    search result.

    Parameters
    -----------------------
    subject_name: str
        The real-world person/event/place name to search for.
    limit: int
        Maximum number of candidates to return (default 5).

    Returns
    -----------------------
    list of dict:
        [{'title': str, 'snippet': str}, ...], empty list if none found.
    """
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': subject_name,
        'format': 'json',
        'srlimit': limit,
    }

    try:
        time.sleep(0.1)
        response = requests.get(url, params=params, headers={'User-Agent': 'MovieAccuracyProject/1.0 (gveettil@umich.edu)'})

        if response.status_code != 200:
            print(f"  Wikipedia search returned status {response.status_code} for '{subject_name}': {response.text[:200]}")
            return []

        results = response.json().get('query', {}).get('search', [])
        candidates = []
        for r in results:
            title = r['title']
            intro = get_wikipedia_article_intro(title)
            snippet = intro if intro else re.sub('<[^>]+>', '', r.get('snippet', ''))
            candidates.append({'title': title, 'snippet': snippet})
        return candidates
    except Exception as e:
        print(f"  Search error for '{subject_name}': {e}")
        return []


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


def _parse_json_array(text, context_label):
    """
    Parses a JSON array out of an LLM response, tolerating markdown code
    fences that models sometimes wrap structured output in.

    Parameters
    -----------------------
    text: str
        The raw LLM response text.
    context_label: str
        A label (e.g. movie title) used in the error message if parsing fails.

    Returns
    -----------------------
    list: The parsed JSON array, or an empty list if parsing failed.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        parsed = json.loads(cleaned)
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError as e:
        print(f"  Failed to parse LLM JSON output for '{context_label}': {e}")
        return []


def identify_real_subjects_with_llm(movie_title, overview):
    """
    Step 1: Uses an LLM to identify the real-world subject(s) -- person(s),
    event(s), or place(s) -- that a movie is based on, from its title and
    TMDB overview. Returns real names only, not Wikipedia article titles;
    resolving a name to the correct article happens in a separate step.

    Parameters
    -----------------------
    movie_title: str
        The movie's title.
    overview: str
        The TMDB overview/description.

    Returns
    -----------------------
    list of dict:
        [{'name': str, 'type': 'Person'|'Event'|'Place'}, ...], empty list
        if no real-world subject could be identified.
    """
    prompt = f"""The film "{movie_title}" is based on a true story. Here is its plot overview:

{overview}

Identify the real-world subject(s) this film is based on -- at most 3, focused on the most central person, event, or place -- but ONLY if the overview gives a specific, distinguishing detail (a real name, a named event, a specific date/place/organization) that lets you confidently pin down which actual person, event, or place is meant.

Do NOT guess based on a generic role or description alone (e.g. "an admiral", "a scientist", "a boxer") when no specific identifying detail is given -- a vague description matches too many real people or events to identify correctly, and a confident-sounding wrong guess is worse than no guess. Treat those cases as unidentifiable.

For each subject you ARE confident about, give its real name (not the movie title) and classify it as one of: Person, Event, Place.

Respond with ONLY a JSON array, no other text, in this exact format:
[{{"name": "...", "type": "Person"}}, ...]

If no real-world subject can be confidently identified, respond with exactly: []"""

    time.sleep(GEMINI_SECONDS_BETWEEN_CALLS)

    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    except genai_errors.APIError as e:
        if e.code == 429:
            raise GeminiRateLimitError(str(e))
        print(f"  Gemini API error identifying subjects for '{movie_title}': {e}")
        return []

    if response.text is None:
        block_reason = getattr(response.prompt_feedback, 'block_reason', None) if response.prompt_feedback else None
        print(f"  Gemini returned no content identifying subjects for '{movie_title}' (block_reason: {block_reason})")
        return []

    return _parse_json_array(response.text, movie_title)


def pick_correct_wikipedia_article_with_llm(movie_title, subject_name, subject_type, candidates):
    """
    Step 2: Given multiple Wikipedia search candidates for a real-world
    subject, uses an LLM to pick the one that's actually the correct
    article -- the same verification idea used for plots in importplots.py,
    but choosing among several candidates instead of confirming just one.

    Parameters
    -----------------------
    movie_title: str
        Context to help disambiguate common names.
    subject_name: str
        The real-world name identified in step 1.
    subject_type: str
        'Person', 'Event', or 'Place'.
    candidates: list of dict
        [{'title': str, 'snippet': str}, ...] from search_wikipedia_candidates.

    Returns
    -----------------------
    str or None:
        The chosen article title, or None if none of the candidates match.
    """
    if not candidates:
        return None

    # A candidate whose title exactly matches the subject name is almost
    # always correct (the subject has its own dedicated article) and is a
    # far more reliable signal than an LLM judging short, sometimes
    # misleading article excerpts -- skip the LLM call entirely in that case.
    for c in candidates:
        if c['title'].strip().lower() == subject_name.strip().lower():
            return c['title']

    candidate_list = "\n".join(
        f"{i + 1}. {c['title']}: {c['snippet']}" for i, c in enumerate(candidates)
    )

    # Sentinel is "UNMATCHED", and the rule avoids phrases like "wrong page"
    # or "disambiguation" -- similar wording previously tripped Gemini's
    # PROHIBITED_CONTENT filter on mature real-world subjects (see the same
    # lesson documented in importplots.py's extract_plot_with_llm).
    prompt = f"""The film "{movie_title}" is based on real events involving a {subject_type.lower()} named "{subject_name}".

Here are Wikipedia search results for that name:
{candidate_list}

Which numbered result is actually the correct Wikipedia article about this specific real-world {subject_type.lower()}? Respond with ONLY that number, with no other text. If none of these results are correct, respond with just the single word UNMATCHED instead."""

    time.sleep(GEMINI_SECONDS_BETWEEN_CALLS)

    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    except genai_errors.APIError as e:
        if e.code == 429:
            raise GeminiRateLimitError(str(e))
        print(f"  Gemini API error picking article for '{subject_name}': {e}")
        return None

    if response.text is None:
        block_reason = getattr(response.prompt_feedback, 'block_reason', None) if response.prompt_feedback else None
        print(f"  Gemini returned no content picking article for '{subject_name}' (block_reason: {block_reason})")
        return None

    result = response.text.strip()
    if not result or result == "UNMATCHED":
        return None

    try:
        index = int(result) - 1
        if 0 <= index < len(candidates):
            return candidates[index]['title']
    except ValueError:
        pass

    print(f"  Unexpected pick response for '{subject_name}': {result!r}")
    return None


def summarize_real_subject_with_llm(subject_name, subject_type, article_text):
    """
    Step 3 (part 1): Uses an LLM to write a concise factual summary of a
    real-world subject from raw Wikipedia article text -- who they were or
    what happened -- trimmed down from the full (often very long) article.

    Parameters
    -----------------------
    subject_name: str
        The real-world name being summarized.
    subject_type: str
        'Person', 'Event', or 'Place'.
    article_text: str
        The full plain-text Wikipedia article.

    Returns
    -----------------------
    str or None:
        The summary text, or None if the article doesn't actually seem to
        be about this subject.
    """
    trimmed_text = article_text[:20000]

    # Same safe-phrasing lesson as importplots.py: avoid "wrong page" /
    # "disambiguation" wording, which previously tripped Gemini's
    # PROHIBITED_CONTENT filter on mature real-world historical subjects.
    prompt = f"""Below is the full text of a Wikipedia article that should be about {subject_name}, a real-world {subject_type.lower()}.

Write a concise factual summary (3-5 sentences) of who or what this {subject_type.lower()} is or was, based only on this article.

Return ONLY the summary text, with no preamble, headers, or commentary. If the article is not about {subject_name}, respond with just the single word UNMATCHED instead.

Article text:
{trimmed_text}"""

    time.sleep(GEMINI_SECONDS_BETWEEN_CALLS)

    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    except genai_errors.APIError as e:
        if e.code == 429:
            raise GeminiRateLimitError(str(e))
        print(f"  Gemini API error summarizing '{subject_name}': {e}")
        return None

    if response.text is None:
        block_reason = getattr(response.prompt_feedback, 'block_reason', None) if response.prompt_feedback else None
        print(f"  Gemini returned no content summarizing '{subject_name}' (block_reason: {block_reason})")
        return None

    result = response.text.strip()
    if not result or result == "UNMATCHED":
        return None
    return result


def resolve_and_store_real_subject(cur, conn, movie_id, movie_title, subject_name, subject_type):
    """
    Step 2 + 3 combined for one identified real-world subject: search
    Wikipedia for candidates, have an LLM pick the correct article, fetch
    and summarize it, then store it in RealSubjects and link it to the
    movie in MovieRealSubjects.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    movie_id: int
    movie_title: str
    subject_name: str
    subject_type: str

    Returns
    -----------------------
    bool: True if the subject was successfully resolved and stored.
    """
    candidates = search_wikipedia_candidates(subject_name)
    article_title = pick_correct_wikipedia_article_with_llm(movie_title, subject_name, subject_type, candidates)

    if not article_title:
        print(f"    No matching Wikipedia article found for '{subject_name}'")
        return False

    article_text = get_wikipedia_article_text(article_title)
    if not article_text:
        print(f"    Could not fetch article text for '{article_title}'")
        return False

    summary = summarize_real_subject_with_llm(subject_name, subject_type, article_text)
    if not summary:
        print(f"    Could not summarize '{article_title}'")
        return False

    subject_id = insert_or_get_real_subject(cur, conn, article_title, subject_type, summary)
    cur.execute('''
        INSERT OR IGNORE INTO MovieRealSubjects (movie_id, subject_id)
        VALUES (?, ?)
    ''', (movie_id, subject_id))
    print(f"    Linked '{subject_name}' -> {article_title}")
    return True


def populate_real_subjects_table(cur, conn, limit=25):
    """
    Populates RealSubjects/MovieRealSubjects for movies that haven't been
    processed yet. For each movie: identifies real-world subjects from its
    overview (step 1), then resolves and stores each one (steps 2-3).
    Movies where no subject can be identified still get a placeholder row
    (subject_id = NULL) so they aren't retried every run.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    limit: int
        Maximum number of movies to process per run (default 25).
    """
    cur.execute('''
        SELECT id, title, overview
        FROM Movies
        WHERE overview IS NOT NULL
        AND id NOT IN (SELECT DISTINCT movie_id FROM MovieRealSubjects)
        LIMIT ?
    ''', (limit,))

    movies_to_process = cur.fetchall()

    if not movies_to_process:
        print("All movies have already been processed for real-world subjects!")
        return

    print(f"Processing {len(movies_to_process)} movies...")

    linked_count = 0
    for movie_id, title, overview in movies_to_process:
        print(f"Identifying real subjects for: {title}")

        try:
            subjects = identify_real_subjects_with_llm(title, overview)

            if not subjects:
                print(f"  No real-world subjects identified for '{title}'")
                cur.execute('''
                    INSERT OR IGNORE INTO MovieRealSubjects (movie_id, subject_id)
                    VALUES (?, NULL)
                ''', (movie_id,))
                continue

            any_linked = False
            for subject in subjects:
                name = subject.get('name')
                subject_type = (subject.get('type') or '').strip().capitalize()
                if not name or subject_type not in ('Person', 'Event', 'Place'):
                    continue

                print(f"  Resolving: {name} ({subject_type})")
                if resolve_and_store_real_subject(cur, conn, movie_id, title, name, subject_type):
                    linked_count += 1
                    any_linked = True

            # If subjects were identified but every one of them failed to
            # resolve (e.g. a persistent safety-filter block on the article
            # content), still mark this movie as checked -- otherwise it
            # gets retried every run, repeatedly re-hitting the same
            # unrecoverable failure for no benefit.
            if not any_linked:
                print(f"  No subjects could be resolved for '{title}'")
                cur.execute('''
                    INSERT OR IGNORE INTO MovieRealSubjects (movie_id, subject_id)
                    VALUES (?, NULL)
                ''', (movie_id,))
        except GeminiRateLimitError as e:
            print(f"\nGemini rate limit hit, stopping this run early: {e}")
            break

    conn.commit()
    print(f"\n{'='*60}")
    print(f"Linked {linked_count} real-world subjects this run.")

    cur.execute('SELECT COUNT(DISTINCT movie_id) FROM MovieRealSubjects')
    total_processed = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Movies WHERE overview IS NOT NULL')
    total_movies = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM RealSubjects')
    total_subjects = cur.fetchone()[0]
    print(f"Total progress: {total_processed}/{total_movies} movies checked for real-world subjects.")
    print(f"Total unique real-world subjects stored: {total_subjects}")


def main():
    cur, conn = set_up_database()
    create_real_subjects_tables(cur, conn)
    populate_real_subjects_table(cur, conn, limit=25)

    conn.close()


if __name__ == "__main__":
    main()
