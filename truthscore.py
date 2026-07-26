import sqlite3
import os
import time
import json
import re
from google import genai
from google.genai import types
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


def create_truth_scores_table(cur, conn):
    """
    Creates the TruthScores table if it doesn't exist. One row per movie
    (1:1 with Movies, like Plots), storing both the individual rubric
    sub-scores and the final computed Truth Index -- keeping the formula's
    inputs auditable rather than just storing a single opaque number.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    cur.execute('''
        CREATE TABLE IF NOT EXISTS TruthScores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER UNIQUE,
            people_score INTEGER,
            events_score INTEGER,
            outcome_score INTEGER,
            timeline_score INTEGER,
            consensus_score INTEGER,
            truth_index INTEGER,
            explanation TEXT,
            FOREIGN KEY (movie_id) REFERENCES Movies(id)
        )
    ''')
    conn.commit()


def get_real_subjects_text(cur, movie_id):
    """
    Builds a combined text block of all real-world subject summaries linked
    to a movie, for feeding into the core-criteria scoring prompt.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    movie_id: int

    Returns
    -----------------------
    str: Combined "[Type] Title: summary" blocks, one per subject, joined
        by blank lines. Empty string if the movie has no linked subjects.
    """
    cur.execute('''
        SELECT rs.subject_type, rs.wikipedia_title, rs.summary
        FROM MovieRealSubjects mrs
        JOIN RealSubjects rs ON mrs.subject_id = rs.id
        WHERE mrs.movie_id = ? AND rs.summary IS NOT NULL
    ''', (movie_id,))

    rows = cur.fetchall()
    return "\n\n".join(f"[{subject_type}] {title}: {summary}" for subject_type, title, summary in rows)


def _extract_json_object(text):
    """
    Extracts a JSON object from an LLM response, tolerating markdown code
    fences and extra surrounding commentary (search-grounded responses in
    particular tend to add source framing around the answer).

    Parameters
    -----------------------
    text: str
        The raw LLM response text.

    Returns
    -----------------------
    dict or None: The parsed JSON object, or None if parsing failed.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def score_core_criteria_with_llm(movie_title, plot_summary, real_subjects_text):
    """
    Rates the film on 4 fixed criteria -- people, events, outcome,
    timeline -- each 0-2, based only on the plot summary and real-subject
    summaries already stored in the database (no external fetching). These
    scores feed directly into compute_truth_index()'s fixed formula.

    Parameters
    -----------------------
    movie_title: str
    plot_summary: str
        The film's fictional plot, from Plots.plot_summary.
    real_subjects_text: str
        Combined real-world subject summaries, from get_real_subjects_text().

    Returns
    -----------------------
    dict or None:
        {'people': {'score': int, 'note': str}, 'events': {...},
         'outcome': {...}, 'timeline': {...}}, or None on failure.
    """
    prompt = f"""You are comparing a movie's fictional plot to the real-world people/events it claims to be based on, to assess historical accuracy.

MOVIE: "{movie_title}"

FICTIONAL PLOT (from the film):
{plot_summary}

REAL-WORLD SUBJECTS (documented facts):
{real_subjects_text}

Rate the film's accuracy on each of these 4 criteria using a 0, 1, or 2 scale:
- people: 0 = real people are fabricated or seriously misrepresented, 1 = some embellishment of real people, 2 = real people portrayed accurately
- events: 0 = major events are fabricated or reversed, 1 = real events present but dramatized or altered, 2 = major events match the documented record
- outcome: 0 = the film's ending contradicts the real outcome, 1 = outcome roughly right but details differ, 2 = ending matches reality
- timeline: 0 = dates or locations are clearly wrong, 1 = minor timeline or setting liberties, 2 = dates and locations are accurate

Respond with ONLY a JSON object, no other text, in this exact format:
{{"people": {{"score": 0, "note": "brief reason"}}, "events": {{"score": 0, "note": "brief reason"}}, "outcome": {{"score": 0, "note": "brief reason"}}, "timeline": {{"score": 0, "note": "brief reason"}}}}"""

    time.sleep(GEMINI_SECONDS_BETWEEN_CALLS)

    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    except genai_errors.APIError as e:
        if e.code == 429:
            raise GeminiRateLimitError(str(e))
        print(f"  Gemini API error scoring core criteria for '{movie_title}': {e}")
        return None

    if response.text is None:
        block_reason = getattr(response.prompt_feedback, 'block_reason', None) if response.prompt_feedback else None
        print(f"  Gemini returned no content scoring '{movie_title}' (block_reason: {block_reason})")
        return None

    parsed = _extract_json_object(response.text)
    if parsed is None or not all(k in parsed for k in ('people', 'events', 'outcome', 'timeline')):
        print(f"  Failed to parse core-criteria JSON for '{movie_title}': {response.text[:200]}")
        return None
    return parsed


def score_consensus_with_llm(movie_title):
    """
    Rates the film's perceived historical accuracy using live Google Search
    grounding (critic reviews, forums, fact-check articles), rather than the
    model's memorized training data. This is the smaller-weighted "hedge"
    variable in the formula -- it's meant to reflect broad internet opinion,
    which is why it searches live instead of using our own stored data.

    Parameters
    -----------------------
    movie_title: str

    Returns
    -----------------------
    dict or None:
        {'score': int, 'note': str}, or None if search/scoring failed.
    """
    prompt = f"""Search for what critics, historians, and general online discussion (reviews, articles, forums, fact-check pieces) say about how historically accurate the film "{movie_title}" is considered to be.

Based on that research, rate the film's perceived historical accuracy on a 0, 1, or 2 scale:
- 0 = widely criticized as inaccurate or heavily fictionalized
- 1 = mixed reception -- some inaccuracies noted alongside praise for accuracy
- 2 = widely regarded as accurate or faithful to real events

Respond with ONLY a JSON object, no other text, in this exact format:
{{"score": 0, "note": "brief summary of what sources say"}}"""

    time.sleep(GEMINI_SECONDS_BETWEEN_CALLS)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            ),
        )
    except genai_errors.APIError as e:
        if e.code == 429:
            raise GeminiRateLimitError(str(e))
        print(f"  Gemini API error getting consensus for '{movie_title}': {e}")
        return None

    if response.text is None:
        block_reason = getattr(response.prompt_feedback, 'block_reason', None) if response.prompt_feedback else None
        print(f"  Gemini returned no content for consensus on '{movie_title}' (block_reason: {block_reason})")
        return None

    parsed = _extract_json_object(response.text)
    if parsed is None or 'score' not in parsed:
        print(f"  Failed to parse consensus JSON for '{movie_title}': {response.text[:200]}")
        return None
    return parsed


def compute_truth_index(people, events, outcome, timeline, consensus=None):
    """
    Combines the rubric scores into a single 0-100 Truth Index using a
    fixed, deterministic formula. The LLM only ever supplies the 0-2
    sub-scores; this arithmetic is identical for every movie.

    people/events/outcome/timeline are weighted 1 each (max 8 total) and
    are the core criteria, computed only from our own stored plot and
    real-subject data. consensus is weighted 0.5 (max 1) since it's a
    smaller hedge informed by live web search, not a core criterion. If
    consensus is unavailable, the formula falls back to the 4 core
    criteria only (denominator drops to 8), rather than penalizing the
    score for missing consensus data.

    Parameters
    -----------------------
    people, events, outcome, timeline: int (each 0-2)
    consensus: int or None (0-2, optional)

    Returns
    -----------------------
    int: Truth Index score from 0 to 100.
    """
    weighted_sum = people + events + outcome + timeline
    max_sum = 8

    if consensus is not None:
        weighted_sum += 0.5 * consensus
        max_sum += 1

    return round(weighted_sum / max_sum * 100)


def populate_truth_scores_table(cur, conn, limit=25):
    """
    Populates TruthScores for movies that have both a plot summary and at
    least one linked real-world subject summary, but no score yet. For
    each movie: scores the 4 core criteria, scores the consensus hedge via
    live search, computes the Truth Index with the fixed formula, and
    stores everything.

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
        SELECT m.id, m.title, p.plot_summary
        FROM Movies m
        JOIN Plots p ON m.id = p.movie_id
        WHERE p.plot_summary IS NOT NULL
        AND m.id NOT IN (SELECT movie_id FROM TruthScores)
        AND EXISTS (
            SELECT 1 FROM MovieRealSubjects mrs
            JOIN RealSubjects rs ON mrs.subject_id = rs.id
            WHERE mrs.movie_id = m.id AND rs.summary IS NOT NULL
        )
        LIMIT ?
    ''', (limit,))

    movies_to_process = cur.fetchall()

    if not movies_to_process:
        print("All eligible movies already have truth scores!")
        return

    print(f"Processing {len(movies_to_process)} movies...")

    scored = 0
    for movie_id, title, plot_summary in movies_to_process:
        print(f"Scoring: {title}")
        real_subjects_text = get_real_subjects_text(cur, movie_id)

        try:
            core = score_core_criteria_with_llm(title, plot_summary, real_subjects_text)
            if core is None:
                print(f"  Skipping '{title}' -- could not score core criteria")
                continue

            consensus = score_consensus_with_llm(title)
        except GeminiRateLimitError as e:
            print(f"\nGemini rate limit hit, stopping this run early: {e}")
            break

        people_score = core['people']['score']
        events_score = core['events']['score']
        outcome_score = core['outcome']['score']
        timeline_score = core['timeline']['score']
        consensus_score = consensus['score'] if consensus else None

        truth_index = compute_truth_index(people_score, events_score, outcome_score, timeline_score, consensus_score)

        explanation = (
            f"People ({people_score}/2): {core['people']['note']}\n"
            f"Events ({events_score}/2): {core['events']['note']}\n"
            f"Outcome ({outcome_score}/2): {core['outcome']['note']}\n"
            f"Timeline ({timeline_score}/2): {core['timeline']['note']}\n"
        )
        explanation += (
            f"Consensus ({consensus_score}/2): {consensus['note']}"
            if consensus else "Consensus: not available"
        )

        cur.execute('''
            INSERT OR REPLACE INTO TruthScores
            (movie_id, people_score, events_score, outcome_score, timeline_score, consensus_score, truth_index, explanation)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (movie_id, people_score, events_score, outcome_score, timeline_score, consensus_score, truth_index, explanation))

        print(f"  Truth Index: {truth_index}")
        scored += 1

    conn.commit()
    print(f"\n{'='*60}")
    print(f"Scored {scored} movies this run.")

    cur.execute('SELECT COUNT(*) FROM TruthScores')
    total_scored = cur.fetchone()[0]
    print(f"Total progress: {total_scored} movies have a Truth Index.")


def main():
    cur, conn = set_up_database()
    create_truth_scores_table(cur, conn)
    populate_truth_scores_table(cur, conn, limit=25)

    conn.close()


if __name__ == "__main__":
    main()
