import sqlite3
import requests
import time
import os


# TMDB API KEY
with open("tmdb_apikey.txt", "r") as f:
    TMDB_API_KEY = f.read().strip()


def set_up_database():
    """
    Sets up a SQLite database connection and cursor.

    Returns
    -----------------------
    Tuple (Cursor, Connection):
        A tuple containing the database cursor and connection objects.
    """
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/movies.db", timeout=10)
    cur = conn.cursor()
    return cur, conn


def setup_tables(cur, conn):
    """
    Creates the normalized database schema for TMDB data:
    - Genres: Unique genre names (no duplicate strings!)
    - MovieGenres: Junction table for many-to-many relationship
    - ReleaseDates: Unique release dates (no duplicate strings!)
    - MovieReleaseDates: Junction table for many-to-many relationship

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    # Genres table - stores unique genre names (no duplicate strings!)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    """)

    # MovieGenres junction table - links movies to genres (many-to-many)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS MovieGenres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            genre_id INTEGER NOT NULL,
            FOREIGN KEY (movie_id) REFERENCES Movies(id),
            FOREIGN KEY (genre_id) REFERENCES Genres(id),
            UNIQUE(movie_id, genre_id)
        )
    """)

    # ReleaseDates table - stores unique release dates (no duplicate strings!)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS ReleaseDates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE NOT NULL
        )
    """)

    # MovieReleaseDates junction table - links movies to release dates
    cur.execute("""
        CREATE TABLE IF NOT EXISTS MovieReleaseDates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            release_date_id INTEGER NOT NULL,
            FOREIGN KEY (movie_id) REFERENCES Movies(id),
            FOREIGN KEY (release_date_id) REFERENCES ReleaseDates(id),
            UNIQUE(movie_id, release_date_id)
        )
    """)

    conn.commit()


def tmdb_search_movie(title):
    """
    Searches TMDB for a movie title and returns the best match.

    Parameters
    -----------------------
    title: str
        The movie title to search for.

    Returns
    -----------------------
    dict or None: First search result from TMDB, or None if not found.
    """
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title,
        "language": "en-US"
    }

    response = requests.get(url, params=params)
    data = response.json()

    results = data.get("results", [])
    if not results:
        return None

    return results[0]


def tmdb_get_movie_details(tmdb_id):
    """
    Gets detailed information about a specific movie from TMDB.

    Parameters
    -----------------------
    tmdb_id: int
        The TMDB ID of the movie.

    Returns
    -----------------------
    dict: Movie details including genres, revenue, release_date, overview, etc.
    """
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY, "language": "en-US"}

    response = requests.get(url, params=params)
    return response.json()


def insert_or_get_genre(cur, conn, genre_name):
    """
    Inserts a genre into the Genres table if it doesn't exist,
    and returns the genre's ID.
    This ensures NO DUPLICATE genre strings in the database.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    genre_name: str
        The name of the genre.

    Returns
    -----------------------
    int: The genre's ID
    """
    # Try to get existing genre
    cur.execute("SELECT id FROM Genres WHERE name = ?", (genre_name,))
    result = cur.fetchone()

    if result:
        return result[0]

    # Insert new genre
    cur.execute("INSERT INTO Genres (name) VALUES (?)", (genre_name,))
    conn.commit()
    return cur.lastrowid


def insert_or_get_release_date(cur, conn, release_date):
    """
    Inserts a release date into the ReleaseDates table if it doesn't exist,
    and returns the release date's ID.
    This ensures NO DUPLICATE release date strings in the database.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    release_date: str
        The release date string.

    Returns
    -----------------------
    int: The release date's ID
    """
    # Try to get existing release date
    cur.execute("SELECT id FROM ReleaseDates WHERE date = ?", (release_date,))
    result = cur.fetchone()

    if result:
        return result[0]

    # Insert new release date
    cur.execute("INSERT INTO ReleaseDates (date) VALUES (?)", (release_date,))
    conn.commit()
    return cur.lastrowid


def populate_tmdb_data(cur, conn, limit=25):
    """
    Fetches TMDB data for movies that don't have it yet.
    Updates Movies table and populates Genres/MovieGenres tables.
    Processes up to 'limit' movies per run (satisfies ≤25 requirement).

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    limit: int
        Maximum number of movies to process per run (default 25).
    """
    # Get movies that don't have TMDB data yet (no tmdb_id)
    cur.execute('''
        SELECT id, title
        FROM Movies
        WHERE tmdb_id IS NULL
        LIMIT ?
    ''', (limit,))

    movies_to_process = cur.fetchall()

    if not movies_to_process:
        print("All movies already have TMDB data!")
        return

    print(f"Processing {len(movies_to_process)} movies...")

    processed = 0
    for movie_id, title in movies_to_process:
        print(f"\nSearching TMDB for: {title}")

        # Search for movie on TMDB
        search_result = tmdb_search_movie(title)
        if search_result is None:
            print(f"  ✗ No TMDB match found for '{title}'")
            continue

        tmdb_id = search_result['id']
        print(f"  ✓ Found on TMDB (ID: {tmdb_id})")

        # Get full movie details
        time.sleep(0.25)  # Rate limiting
        details = tmdb_get_movie_details(tmdb_id)

        # Update Movies table with TMDB data (release_date now stored in ReleaseDates table)
        cur.execute("""
            UPDATE Movies
            SET tmdb_id = ?,
                revenue = ?,
                overview = ?
            WHERE id = ?
        """, (
            details.get('id'),
            details.get('revenue', 0),
            details.get('overview'),
            movie_id
        ))

        # Insert genres using normalized structure (no duplicate strings!)
        genres = details.get('genres', [])
        for genre_data in genres:
            genre_name = genre_data['name']
            # Get or create genre (ensures uniqueness)
            genre_id = insert_or_get_genre(cur, conn, genre_name)

            # Link movie to genre
            cur.execute("""
                INSERT OR IGNORE INTO MovieGenres (movie_id, genre_id)
                VALUES (?, ?)
            """, (movie_id, genre_id))

        # Insert release date using normalized structure (no duplicate strings!)
        release_date = details.get('release_date')
        if release_date:
            # Get or create release date (ensures uniqueness)
            release_date_id = insert_or_get_release_date(cur, conn, release_date)

            # Link movie to release date
            cur.execute("""
                INSERT OR IGNORE INTO MovieReleaseDates (movie_id, release_date_id)
                VALUES (?, ?)
            """, (movie_id, release_date_id))

        conn.commit()
        processed += 1
        print(f"  ✓ Saved: {details.get('title')} with {len(genres)} genres")

    print(f"\n{'='*60}")
    print(f"Processed {processed} new movies")

    # Show progress
    cur.execute("SELECT COUNT(*) FROM Movies WHERE tmdb_id IS NOT NULL")
    total_with_tmdb = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Movies")
    total_movies = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM Genres")
    total_genres = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM MovieGenres")
    total_genre_links = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM ReleaseDates")
    total_release_dates = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM MovieReleaseDates")
    total_date_links = cur.fetchone()[0]

    print(f"Total progress: {total_with_tmdb}/{total_movies} movies have TMDB data")
    print(f"Total unique genres: {total_genres}")
    print(f"Total movie-genre links: {total_genre_links}")
    print(f"Total unique release dates: {total_release_dates}")
    print(f"Total movie-release date links: {total_date_links}")
    print("="*60)


def main():
    """
    Main function: Fetches TMDB data for movies in the database.
    Run importmovielist.py first to populate movie titles.
    """
    cur, conn = set_up_database()

    print("="*60)
    print("STEP 2: Fetching TMDB Data for Movies")
    print("="*60)

    setup_tables(cur, conn)
    populate_tmdb_data(cur, conn, limit=25)

    print("\nNext step: Run moviecalc.py to categorize movies")
    conn.close()


if __name__ == "__main__":
    main()
