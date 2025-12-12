from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

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

    Parameters
    -----------------------
    db_name: str
        The name of the SQLite database.

    Returns
    -----------------------
    Tuple (Cursor, Connection):
        A tuple containing the database cursor and connection objects.
    """
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/movies.db")
    cur = conn.cursor()
    return cur, conn

def get_true_story_movies():
    """
    Scrapes a webpage to get a list of movies based on true stories from IMDb.
    Uses Selenium to handle infinite scroll and fetch all 250 movies.

    Returns
    -----------------------
    List of str:
        A list containing the titles of movies based on true stories.
    """
    url = 'https://www.imdb.com/list/ls021398170/'

    # Set up Chrome options for headless browsing
    chrome_options = Options()
    chrome_options.add_argument('--headless')  # Run in background
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    print("Starting browser...")
    # Initialize the Chrome driver
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        print("Loading IMDb page...")
        driver.get(url)

        # Wait for the page to load
        time.sleep(3)

        # Scroll to load all movies
        print("Scrolling to load all movies...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        movies_loaded = 0

        while True:
            # Scroll down to the bottom
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            # Wait for new content to load
            time.sleep(2)

            # Check current number of movies loaded
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            items = soup.find_all('li', class_='ipc-metadata-list-summary-item')
            current_count = len(items)

            print(f"Loaded {current_count} movies so far...")

            # Calculate new scroll height and compare with last scroll height
            new_height = driver.execute_script("return document.body.scrollHeight")

            # Break if we've loaded all 250 movies or if no new content loaded
            if current_count >= 250 or (new_height == last_height and current_count == movies_loaded):
                print(f"Finished loading. Total: {current_count} movies")
                break

            last_height = new_height
            movies_loaded = current_count

        # Parse the final page content
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        items = soup.find_all('li', class_='ipc-metadata-list-summary-item')

        movies = []
        for item in items:
            title_tag = item.find('h3', class_='ipc-title__text')
            if title_tag is not None:
                title = title_tag.text.strip()
                # Remove the number prefix (e.g., "1. ", "25. ")
                if '. ' in title:
                    title = title.split('. ', 1)[1]
                movies.append(title)

        print(f"Total movies fetched: {len(movies)}")
        return movies

    finally:
        # Close the browser
        driver.quit()
        print("Browser closed.")

def setup_movies_table(cur, conn):
    """
    Creates the Movies table with basic structure.
    TMDB data will be added later by tmdbdata.py

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            tmdb_id INTEGER UNIQUE,
            release_date TEXT,
            revenue INTEGER,
            overview TEXT
        )
    """)
    conn.commit()

def populate_movies_table(cur, conn, movie_titles):
    """
    Populates the Movies table in the database with movie titles ONLY.
    TMDB data (genres, revenue, overview) will be fetched by tmdbdata.py

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    movie_titles: List of str
        A list of movie titles to insert into the database.
    """
    setup_movies_table(cur, conn)

    inserted = 0
    for title in movie_titles:
        cur.execute("INSERT OR IGNORE INTO Movies (title) VALUES (?)", (title,))
        if cur.rowcount > 0:
            inserted += 1

    conn.commit()

    print(f"\n{'='*60}")
    print(f"Inserted {inserted} new movies")
    cur.execute("SELECT COUNT(*) FROM Movies")
    total = cur.fetchone()[0]
    print(f"Total movies in database: {total}")
    print("="*60)

def main():
    """
    Main function: Scrapes IMDb for true story movies and inserts titles into database.
    Run tmdbdata.py next to fetch detailed information from TMDB.
    """
    cur, conn = set_up_database()
    print("="*60)
    print("STEP 1: Scraping IMDb for True Story Movies")
    print("="*60)

    true_story_movies = get_true_story_movies()
    populate_movies_table(cur, conn, true_story_movies)

    print("\nNext step: Run tmdbdata.py to fetch details from TMDB API")
    conn.close()

if __name__ == "__main__":
    main()