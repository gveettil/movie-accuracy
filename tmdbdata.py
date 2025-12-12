import sqlite3
import requests
import time
import os


# TMDB API KEY

with open("tmdb_apikey.txt", "r") as f:
    TMDB_API_KEY = f.read().strip()


# Database connection

def set_up_database():
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/movies.db", timeout=10)
    cur = conn.cursor()
    return cur, conn



# TMDB API Helpers

def tmdb_search_movie(title):
    """
    Searches TMDB for a movie title and returns TMDB ID.
    """
    url = "https://api.themoviedb.org/3/search/movie"
    params = {
        "api_key": TMDB_API_KEY,
        "query": title
    }

    resp = requests.get(url, params=params)
    data = resp.json()

    results = data.get("results", [])
    if not results:
        return None
    return results[0]["id"]


def tmdb_get_movie_details(tmdb_id):
    """
    Returns genres, release_date, and revenue for a TMDB ID.
    """
    url = f"https://api.themoviedb.org/3/movie/{tmdb_id}"
    params = {"api_key": TMDB_API_KEY}

    resp = requests.get(url, params=params)
    data = resp.json()

    genres = ", ".join([g["name"] for g in data.get("genres", [])])

    return {
        "tmdb_id": data.get("id"),
        "genres": genres,
        "release_date": data.get("release_date"),
        "revenue": data.get("revenue", 0)
    }



# TMDB Table Setup

def setup_tmdb_table(cur, conn):
    cur.execute("""
        CREATE TABLE IF NOT EXISTS TMDB_Data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER UNIQUE,
            tmdb_id INTEGER,
            genres TEXT,
            release_date TEXT,
            revenue INTEGER,
            FOREIGN KEY(movie_id) REFERENCES Movies(id)
        )
    """)
    conn.commit()



# Populate TMDB_Data (≤25 per run)

def populate_tmdb_table(cur, conn, limit=25):
    """
    Fetch TMDB data for up to 25 movies not yet processed.
    Satisfies rubric requirement.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    limit: int
        Maximum number of movies to process per run (default 25).
    """

    # Get movies that don't have TMDB data yet
    cur.execute('''
        SELECT id, title
        FROM Movies
        WHERE id NOT IN (SELECT movie_id FROM TMDB_Data)
        LIMIT ?
    ''', (limit,))

    to_process = cur.fetchall()

    if not to_process:
        print("All movies already have TMDB data!")
        return

    print(f"Processing {len(to_process)} movies...")

    for movie_id, title in to_process:
        print(f"\nFetching TMDB for: {title}")

        tmdb_id = tmdb_search_movie(title)
        if tmdb_id is None:
            print("  TMDB match not found.")
            continue

        details = tmdb_get_movie_details(tmdb_id)

        cur.execute("""
            INSERT OR REPLACE INTO TMDB_Data
            (movie_id, tmdb_id, genres, release_date, revenue)
            VALUES (?, ?, ?, ?, ?)
        """, (
            movie_id,
            details["tmdb_id"],
            details["genres"],
            details["release_date"],
            details["revenue"]
        ))

        conn.commit()
        print(f"  Saved TMDB data for '{title}'.")
        time.sleep(1)  # short break for tmdb api rate limit

    print("\nTMDB population run complete.")

    # Show progress
    cur.execute('SELECT COUNT(*) FROM TMDB_Data')
    total_processed = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Movies')
    total_movies = cur.fetchone()[0]
    print(f"Total progress: {total_processed}/{total_movies} movies have TMDB data.")



def main():
    cur, conn = set_up_database()
    setup_tmdb_table(cur, conn)
    populate_tmdb_table(cur, conn, limit=25)
    conn.close()


if __name__ == "__main__":
    main()