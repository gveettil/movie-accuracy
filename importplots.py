from bs4 import BeautifulSoup
import re
import os
import csv
import requests
import unittest
import sqlite3
import json
import time


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
    Searches Wikipedia for articles matching the movie title.

    Parameters
    -----------------------
    movie_title: str
        The title of the movie to search for.

    Returns
    -----------------------
    str or None:
        The best matching Wikipedia page title if found, None otherwise.
    """
    search_url = "https://en.wikipedia.org/w/api.php"
    params = {
        'action': 'query',
        'list': 'search',
        'srsearch': movie_title + ' film',
        'format': 'json',
        'srlimit': 5  # Get top 5 results
    }

    try:
        time.sleep(0.1)
        response = requests.get(search_url, params=params, headers={'User-Agent': 'MovieAccuracyProject/1.0'})

        if response.status_code == 200:
            data = response.json()
            search_results = data.get('query', {}).get('search', [])

            if search_results:
                # Return the title of the first (best) match
                best_match = search_results[0]['title']
                print(f"  Found Wikipedia match: {best_match}")
                return best_match

        return None
    except Exception as e:
        print(f"  Search error for {movie_title}: {e}")
        return None


def get_wikipedia_plot(movie_title):
    """
    Fetches the plot summary from Wikipedia's REST API for a given movie title.
    Uses Wikipedia search to find the article if direct lookup fails.

    Parameters
    -----------------------
    movie_title: str
        The title of the movie.

    Returns
    -----------------------
    str or None:
        The plot summary text if found, None otherwise.
    """
    # Format the title for Wikipedia URL (replace spaces with underscores)
    formatted_title = movie_title.replace(' ', '_')

    # Wikipedia REST API endpoint for HTML content
    url = f"https://en.wikipedia.org/api/rest_v1/page/html/{formatted_title}"

    try:
        # Add delay to be respectful to Wikipedia's API
        time.sleep(0.1)

        response = requests.get(url, headers={'User-Agent': 'MovieAccuracyProject/1.0'})

        if response.status_code == 200:
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Find the Plot section within <section> elements
            plot_section = None
            for section in soup.find_all('section'):
                heading = section.find(['h2', 'h3'])
                if heading:
                    heading_text = heading.get_text().strip().lower()
                    if 'plot' in heading_text or 'synopsis' in heading_text or 'summary' in heading_text or 'story' in heading_text or 'premise' in heading_text:
                        plot_section = section
                        break

            if plot_section:
                # Collect all paragraphs from the section
                plot_text = []
                for paragraph in plot_section.find_all('p'):
                    text = paragraph.get_text().strip()
                    if text:
                        plot_text.append(text)

                if plot_text:
                    return ' '.join(plot_text)



        # If we got 404 or no plot was found, try searching
        if response.status_code == 404 or response.status_code == 200:
            print(f"  Direct lookup failed, searching Wikipedia...")
            # Try searching for the article
            search_result = search_wikipedia(movie_title)
            if search_result:
                # Recursively call with the found title (but only once to avoid infinite loop)
                formatted_search_title = search_result.replace(' ', '_')
                search_url = f"https://en.wikipedia.org/api/rest_v1/page/html/{formatted_search_title}"

                time.sleep(0.1)
                search_response = requests.get(search_url, headers={'User-Agent': 'MovieAccuracyProject/1.0'})

                if search_response.status_code == 200:
                    soup = BeautifulSoup(search_response.text, 'html.parser')

                    plot_section = None
                    for section in soup.find_all('section'):
                        heading = section.find(['h2', 'h3'])
                        if heading:
                            heading_text = heading.get_text().strip().lower()
                            if 'plot' in heading_text or 'synopsis' in heading_text:
                                plot_section = section
                                break

                    if plot_section:
                        plot_text = []
                        for paragraph in plot_section.find_all('p'):
                            text = paragraph.get_text().strip()
                            if text:
                                plot_text.append(text)

                        if plot_text:
                            return ' '.join(plot_text)

            print(f"  Wikipedia page not found for: {movie_title}")
            return None
        else:
            print(f"  Error fetching {movie_title}: Status {response.status_code}")
            return None

    except Exception as e:
        print(f"  Exception fetching {movie_title}: {e}")
        return None


def populate_plots_table(cur, conn, limit=25):
    """
    Populates the Plots table with plot summaries from Wikipedia.
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
    # Get movies that don't have plots yet OR have NULL plot summaries
    cur.execute('''
        SELECT id, title
        FROM Movies
        WHERE id NOT IN (SELECT movie_id FROM Plots WHERE plot_summary IS NOT NULL)
        LIMIT ?
    ''', (limit,))

    movies_to_process = cur.fetchall()

    if not movies_to_process:
        print("All movies already have plots stored!")
        return

    print(f"Processing {len(movies_to_process)} movies...")

    successful = 0
    for movie_id, title in movies_to_process:
        print(f"Fetching plot for: {title}")
        plot = get_wikipedia_plot(title)

        if plot:
            # Use INSERT OR REPLACE to update existing NULL entries
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

    # Show progress
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
