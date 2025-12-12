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

def populate_tmdb_table(cur, conn):
    """
    Fetch TMDB data for up to 25 movies not yet processed.
    Satisfies rubric requirement.
    """

    # Get all movies from Movies table
    cur.execute("SELECT id, title FROM Movies")
    all_movies = cur.fetchall()

    # Get processed movie IDs from TMDB_Data table
    cur.execute("SELECT movie_id FROM TMDB_Data")
    processed_ids = {row[0] for row in cur.fetchall()}

    # Filter movies needing TMDB data; cap at 25
    to_process = [(mid, title) for mid, title in all_movies if mid not in processed_ids]
    to_process = to_process[:25]

    print(f"Processing {len(to_process)} new TMDB entries (max 25).")

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



def main():
    cur, conn = set_up_database()
    setup_tmdb_table(cur, conn)
    populate_tmdb_table(cur, conn)
    conn.close()


if __name__ == "__main__":
    main()