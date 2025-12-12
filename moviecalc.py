import sqlite3
import os
import requests
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


def create_subject_categories_table(cur, conn):
    """
    Creates the Subject_Categories table to store categorized subjects.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    cur.execute('''
        CREATE TABLE IF NOT EXISTS Subject_Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER UNIQUE,
            movie_title TEXT,
            category TEXT,
            occupation TEXT,
            is_person BOOLEAN,
            FOREIGN KEY (movie_id) REFERENCES True_Story_Movies(id)
        )
    ''')
    conn.commit()


def categorize_subject_from_plot(title, plot_summary, genres):
    """
    Categorizes a movie's subject based on plot summary and TMDB genres.

    Parameters
    -----------------------
    title: str
        The movie title.
    plot_summary: str
        The Wikipedia plot summary.
    genres: str
        The TMDB genres (comma-separated).

    Returns
    -----------------------
    tuple (str, str, bool):
        (category, occupation, is_person) where category is the broad type,
        occupation is more specific, and is_person indicates if it's about a person.
    """
    if not plot_summary:
        return "Unknown", None, False

    # Convert to lowercase for easier searching
    plot_lower = plot_summary.lower()
    title_lower = title.lower()
    genres_lower = genres.lower() if genres else ""

    # Category classification
    category = "Other"
    occupation = None
    is_person = True  # Default assumption for true story movies

    # Athletes & Sports
    sports_keywords = ['athlete', 'sport', 'football', 'basketball', 'baseball', 'boxer', 'boxing',
                      'tennis', 'olympic', 'racing', 'race car', 'soccer', 'hockey', 'championship',
                      'coach', 'team', 'player', 'game', 'match', 'tournament']
    if any(word in plot_lower for word in sports_keywords) or 'sport' in genres_lower:
        category = "Athletes"
        if 'boxer' in plot_lower or 'boxing' in plot_lower:
            occupation = "Boxer"
        elif 'football' in plot_lower:
            occupation = "Football Player"
        elif 'basketball' in plot_lower:
            occupation = "Basketball Player"
        elif 'baseball' in plot_lower:
            occupation = "Baseball Player"
        elif 'racing' in plot_lower or 'race car' in plot_lower or 'driver' in plot_lower:
            occupation = "Race Car Driver"
        elif 'coach' in plot_lower:
            occupation = "Coach"
        else:
            occupation = "Athlete"

    # Musicians & Performers
    elif any(word in plot_lower for word in ['musician', 'singer', 'composer', 'pianist', 'band',
                                              'music', 'song', 'concert', 'album', 'rapper', 'guitar']):
        category = "Musicians"
        if 'pianist' in plot_lower:
            occupation = "Pianist"
        elif 'singer' in plot_lower or 'vocalist' in plot_lower:
            occupation = "Singer"
        elif 'rapper' in plot_lower or 'rap' in plot_lower:
            occupation = "Rapper"
        elif 'composer' in plot_lower:
            occupation = "Composer"
        elif 'band' in plot_lower:
            occupation = "Band Member"
        else:
            occupation = "Musician"

    # Criminals & Outlaws
    elif any(word in plot_lower for word in ['criminal', 'gangster', 'murder', 'killer', 'mob',
                                              'mafia', 'drug', 'cartel', 'prison', 'fbi', 'arrest',
                                              'crime', 'heist', 'robbery', 'outlaw']):
        category = "Criminals"
        if 'serial killer' in plot_lower:
            occupation = "Serial Killer"
        elif 'gangster' in plot_lower or 'mobster' in plot_lower or 'mafia' in plot_lower:
            occupation = "Gangster"
        elif 'drug' in plot_lower and 'cartel' in plot_lower:
            occupation = "Drug Dealer"
        else:
            occupation = "Criminal"

    # Military & War
    elif any(word in plot_lower for word in ['military', 'soldier', 'general', 'war', 'battle',
                                              'army', 'navy', 'marine', 'combat', 'troop', 'officer',
                                              'colonel', 'sergeant', 'veteran', 'squadron']):
        category = "Military"
        if 'general' in plot_lower:
            occupation = "General"
        elif 'pilot' in plot_lower:
            occupation = "Pilot"
        elif 'navy' in plot_lower or 'admiral' in plot_lower:
            occupation = "Naval Officer"
        else:
            occupation = "Military Personnel"

    # Scientists & Academics
    elif any(word in plot_lower for word in ['scientist', 'mathematician', 'physicist', 'professor',
                                              'researcher', 'theory', 'discover', 'invention', 'academic']):
        category = "Scientists"
        if 'mathematician' in plot_lower:
            occupation = "Mathematician"
        elif 'physicist' in plot_lower:
            occupation = "Physicist"
        elif 'professor' in plot_lower:
            occupation = "Professor"
        else:
            occupation = "Scientist"

    # Activists & Social Figures
    elif any(word in plot_lower for word in ['activist', 'civil rights', 'protest', 'movement',
                                              'rights', 'equality', 'discrimination', 'segregation']):
        category = "Activists"
        occupation = "Activist"

    # Politicians & Leaders
    elif any(word in plot_lower for word in ['president', 'prime minister', 'governor', 'senator',
                                              'politician', 'election', 'campaign', 'congress', 'parliament']):
        category = "Politicians"
        if 'president' in plot_lower:
            occupation = "President"
        elif 'prime minister' in plot_lower:
            occupation = "Prime Minister"
        elif 'senator' in plot_lower:
            occupation = "Senator"
        else:
            occupation = "Politician"

    # Businesspeople & Entrepreneurs
    elif any(word in plot_lower for word in ['business', 'entrepreneur', 'company', 'ceo', 'founder',
                                              'corporation', 'billionaire', 'fortune', 'industry']):
        category = "Businesspeople"
        if 'billionaire' in plot_lower:
            occupation = "Billionaire"
        elif 'ceo' in plot_lower or 'founder' in plot_lower:
            occupation = "CEO/Founder"
        else:
            occupation = "Businessperson"

    # Artists & Writers
    elif any(word in plot_lower for word in ['artist', 'painter', 'writer', 'author', 'novel',
                                              'book', 'journalist', 'reporter', 'paint', 'artwork']):
        category = "Artists & Writers"
        if 'painter' in plot_lower or 'paint' in plot_lower:
            occupation = "Painter"
        elif 'writer' in plot_lower or 'author' in plot_lower:
            occupation = "Writer"
        elif 'journalist' in plot_lower or 'reporter' in plot_lower:
            occupation = "Journalist"
        else:
            occupation = "Artist"

    # Entertainers (Actors, Directors, etc.)
    elif any(word in plot_lower for word in ['actor', 'actress', 'director', 'film', 'movie',
                                              'hollywood', 'performance', 'stage']):
        category = "Entertainers"
        if 'director' in plot_lower:
            occupation = "Director"
        else:
            occupation = "Actor"

    # Historical Events (check for event-focused narratives)
    elif any(word in title_lower for word in ['disaster', 'attack', 'operation', 'mission', 'incident']) or \
         (('war' in genres_lower or 'history' in genres_lower) and
          not any(person_word in plot_lower[:500] for person_word in ['he ', 'she ', 'his ', 'her ', 'him '])):
        category = "Historical Events"
        occupation = None
        is_person = False

    return category, occupation, is_person


def populate_subject_categories(cur, conn, limit=25):
    """
    Populates the Subject_Categories table by categorizing subjects.
    Processes up to 'limit' entries per run.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    limit: int
        Maximum number of entries to process per run (default 25).
    """
    # Get subjects that haven't been categorized yet
    cur.execute('''
        SELECT movie_id, real_article_title
        FROM True_Story_Data
        WHERE real_article_title IS NOT NULL
        AND movie_id NOT IN (SELECT movie_id FROM Subject_Categories)
        LIMIT ?
    ''', (limit,))

    subjects_to_process = cur.fetchall()

    if not subjects_to_process:
        print("All subjects have been categorized!")
        return

    print(f"Categorizing {len(subjects_to_process)} subjects...")

    for movie_id, article_title in subjects_to_process:
        print(f"\nProcessing: {article_title}")

        # Fetch Wikipedia categories
        categories = get_wikipedia_categories(article_title)
        print(f"  Found {len(categories)} Wikipedia categories")

        # Categorize the subject
        category, occupation, is_person = categorize_subject(article_title, categories)
        print(f"  Category: {category}, Occupation: {occupation}, Is Person: {is_person}")

        # Store in database
        cur.execute('''
            INSERT OR REPLACE INTO Subject_Categories
            (movie_id, subject_name, category, occupation, is_person)
            VALUES (?, ?, ?, ?, ?)
        ''', (movie_id, article_title, category, occupation, is_person))

    conn.commit()
    print(f"\n{'='*60}")
    print(f"Successfully categorized {len(subjects_to_process)} subjects.")

    # Show progress
    cur.execute('SELECT COUNT(*) FROM Subject_Categories')
    total_categorized = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM True_Story_Data WHERE real_article_title IS NOT NULL')
    total_subjects = cur.fetchone()[0]
    print(f"Total progress: {total_categorized}/{total_subjects} subjects categorized.")


def calculate_statistics(cur, conn):
    """
    Performs calculations on the categorized data and writes results to a file.
    This function joins multiple tables and computes statistics.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    print("\n" + "="*60)
    print("CALCULATING STATISTICS")
    print("="*60)

    # Open output file for writing calculations
    output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'calculations_output.txt')
    with open(output_file, 'w') as f:
        f.write("="*60 + "\n")
        f.write("TRUE STORY MOVIE SUBJECT ANALYSIS - CALCULATIONS\n")
        f.write("="*60 + "\n\n")

        # 1. Count movies by category (JOIN True_Story_Movies, Subject_Categories)
        f.write("1. COUNT OF MOVIES BY SUBJECT CATEGORY\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT sc.category, COUNT(*) as movie_count
            FROM Subject_Categories sc
            JOIN True_Story_Movies tsm ON sc.movie_id = tsm.id
            GROUP BY sc.category
            ORDER BY movie_count DESC
        ''')

        category_counts = cur.fetchall()
        for category, count in category_counts:
            line = f"{category}: {count} movies\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 2. Person vs Non-Person breakdown
        f.write("2. MOVIES ABOUT PEOPLE VS EVENTS/BOOKS\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT
                CASE WHEN is_person = 1 THEN 'About People' ELSE 'About Events/Books' END as type,
                COUNT(*) as count
            FROM Subject_Categories
            GROUP BY is_person
        ''')

        person_stats = cur.fetchall()
        for type_name, count in person_stats:
            line = f"{type_name}: {count} movies\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 3. Top 10 most common occupations
        f.write("3. TOP 10 MOST COMMON OCCUPATIONS\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT occupation, COUNT(*) as count
            FROM Subject_Categories
            WHERE occupation IS NOT NULL
            GROUP BY occupation
            ORDER BY count DESC
            LIMIT 10
        ''')

        occupation_stats = cur.fetchall()
        for occupation, count in occupation_stats:
            line = f"{occupation}: {count} movies\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 4. Category with genre data (JOIN with TMDB_Data and Movies)
        f.write("4. SUBJECT CATEGORIES WITH MOST COMMON MOVIE GENRES\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT sc.category, td.genres, COUNT(*) as count
            FROM Subject_Categories sc
            JOIN True_Story_Movies tsm ON sc.movie_id = tsm.id
            JOIN Movies m ON tsm.title = m.title
            JOIN TMDB_Data td ON m.id = td.movie_id
            WHERE td.genres IS NOT NULL AND td.genres != ''
            GROUP BY sc.category, td.genres
            ORDER BY sc.category, count DESC
        ''')

        genre_by_category = cur.fetchall()
        current_category = None
        for category, genres, count in genre_by_category:
            if category != current_category:
                f.write(f"\n{category}:\n")
                print(f"\n{category}:")
                current_category = category
            line = f"  {genres}: {count} movies\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 5. Average revenue by subject category (JOIN)
        f.write("5. AVERAGE REVENUE BY SUBJECT CATEGORY (in millions USD)\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT sc.category, AVG(td.revenue) / 1000000.0 as avg_revenue_millions, COUNT(*) as movie_count
            FROM Subject_Categories sc
            JOIN True_Story_Movies tsm ON sc.movie_id = tsm.id
            JOIN Movies m ON tsm.title = m.title
            JOIN TMDB_Data td ON m.id = td.movie_id
            WHERE td.revenue > 0
            GROUP BY sc.category
            ORDER BY avg_revenue_millions DESC
        ''')

        revenue_stats = cur.fetchall()
        for category, avg_revenue, movie_count in revenue_stats:
            line = f"{category}: ${avg_revenue:.2f}M (based on {movie_count} movies)\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 6. Sample movies from each category
        f.write("6. SAMPLE MOVIES FROM EACH CATEGORY\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT sc.category, tsm.title, sc.subject_name
            FROM Subject_Categories sc
            JOIN True_Story_Movies tsm ON sc.movie_id = tsm.id
            ORDER BY sc.category, tsm.title
        ''')

        all_samples = cur.fetchall()
        current_category = None
        count_in_category = 0
        for category, title, subject in all_samples:
            if category != current_category:
                f.write(f"\n{category}:\n")
                print(f"\n{category}:")
                current_category = category
                count_in_category = 0

            if count_in_category < 3:  # Show only 3 examples per category
                line = f"  - {title} (about {subject})\n"
                f.write(line)
                print(line.strip())
                count_in_category += 1

        f.write("\n" + "="*60 + "\n")
        f.write("END OF CALCULATIONS\n")
        f.write("="*60 + "\n")

    print(f"\n{'='*60}")
    print(f"Calculations saved to: {output_file}")
    print("="*60)


def main():
    cur, conn = set_up_database()
    create_subject_categories_table(cur, conn)
    populate_subject_categories(cur, conn, limit=25)

    # After all data is collected, run calculations
    cur.execute('SELECT COUNT(*) FROM Subject_Categories')
    categorized_count = cur.fetchone()[0]

    if categorized_count > 0:
        print("\nRunning calculations on categorized data...")
        calculate_statistics(cur, conn)
    else:
        print("\nNo categorized data yet. Run this script multiple times to categorize all subjects.")

    conn.close()


if __name__ == "__main__":
    main()
