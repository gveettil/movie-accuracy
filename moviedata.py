from bs4 import BeautifulSoup

import re
import os
import csv
import requests
import unittest
import sqlite3
import json
import os
import matplotlib.pyplot as plt


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
    Scrapes a webpage to get a list of movies based on true stories.

    Returns
    -----------------------
    List of str:
        A list containing the titles of movies based on true stories.
    """
    url = 'https://www.flickchart.com/charts.aspx?genre=based-on-a-true-story&perpage=250'
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    movies = []

    divs = soup.find_all('div', class_='movieDetails')
    for div in divs:
        if div is not None:
            title_tag = div.find('span', itemprop='name')
            if title_tag is not None:
                title = title_tag.text.strip()
                movies.append(title)

    return movies

def populate_true_story_movies_table(cur, conn, true_story_movies):
    """
    Populates the True_Story_Movies table in the database with movie titles.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    true_story_movies: List of str
        A list of movie titles based on true stories.
    """
    cur.execute('''
        CREATE TABLE IF NOT EXISTS True_Story_Movies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT UNIQUE
        )
    ''')
    for movie in true_story_movies:
        cur.execute('INSERT OR IGNORE INTO True_Story_Movies (title) VALUES (?)', (movie,))
    conn.commit()

def main (): 
    cur, conn = set_up_database()
    true_story_movies = get_true_story_movies()
    populate_true_story_movies_table(cur, conn, true_story_movies)
    conn.close()

if __name__ == "__main__":
    main()