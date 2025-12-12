import sqlite3
import os


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


def create_categories_tables(cur, conn):
    """
    Creates the normalized Categories tables:
    - Categories: Unique category names (no duplicates!)
    - MovieCategories: Junction table linking movies to categories

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    """
    # Categories table - stores unique category names (like Genres table)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS Categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')

    # MovieCategories junction table - links movies to categories (like MovieGenres)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS MovieCategories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            movie_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (movie_id) REFERENCES Movies(id),
            FOREIGN KEY (category_id) REFERENCES Categories(id),
            UNIQUE(movie_id, category_id)
        )
    ''')
    conn.commit()


def insert_or_get_category(cur, conn, category_name):
    """
    Inserts a category into the Categories table if it doesn't exist,
    and returns the category's ID.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    conn: Connection
        The database connection.
    category_name: str
        The name of the category.

    Returns
    -----------------------
    int: The category's ID
    """
    # Try to get existing category
    cur.execute("SELECT id FROM Categories WHERE name = ?", (category_name,))
    result = cur.fetchone()

    if result:
        return result[0]

    # Insert new category
    cur.execute("INSERT INTO Categories (name) VALUES (?)", (category_name,))
    conn.commit()
    return cur.lastrowid


def categorize_subject_from_overview(title, overview, genre_names):
    """
    Categorizes a movie's subject based on TMDB overview and genres.

    Parameters
    -----------------------
    title: str
        The movie title.
    overview: str
        The TMDB overview/description.
    genre_names: str
        Comma-separated genre names from joined query.

    Returns
    -----------------------
    str: The category (broad subject type)
    """
    if not overview:
        return "Other"

    # Convert to lowercase for easier searching
    overview_lower = overview.lower()
    title_lower = title.lower()
    genres_lower = genre_names.lower() if genre_names else ""

    # Category classification based on keywords
    # Order matters! Check more specific categories first
    category = "Other"

    # Musicians & Performers (check first - very specific keywords)
    if any(word in overview_lower for word in ['musician', 'singer', 'vocalist', 'composer', 'band member',
                                            'performs', 'concert', 'album', 'rapper', 'hip hop', 'pianist', 'piano',
                                            'musical family', 'selena']):
        category = "Musicians"

    # Athletes & Sports (check early - specific keywords)
    elif any(word in overview_lower for word in ['boxer', 'boxing', 'football', 'basketball', 'baseball',
                                              'olympic', 'race car', 'racing driver', 'quarterback', 'athlete',
                                              'coach', 'sport', 'mixed martial', 'mma', 'fighter']):
        category = "Athletes"

    # Scientists & Academics (check BEFORE military - scientists often involved in war projects)
    elif any(word in overview_lower for word in ['scientist', 'mathematician', 'physicist', 'professor',
                                              'researcher', 'theory', 'discover', 'invention', 'academic',
                                              'cryptanalyst', 'oppenheimer', 'turing', 'atomic bomb',
                                              'enigma', 'code', 'cipher', 'computation']):
        category = "Scientists"

    # Activists & Social Figures (check BEFORE criminals/military - slavery, civil rights)
    elif any(word in overview_lower for word in ['activist', 'civil rights', 'protest', 'movement',
                                              'rights', 'equality', 'discrimination', 'segregation',
                                              'slavery', 'slave', 'freedom', 'abolitionist', 'black panthers',
                                              'free black man']):
        category = "Activists"

    # Businesspeople & Entrepreneurs
    elif any(word in overview_lower for word in ['entrepreneur', 'ceo', 'founder', 'billionaire',
                                              'creates a company', 'starts a business', 'facebook', 'zuckerberg',
                                              'businessman']):
        category = "Businesspeople"

    # Artists & Writers (check before journalists)
    elif any(word in overview_lower for word in ['artist', 'painter', 'writer', 'author', 'novel',
                                              'book', 'paint', 'artwork', 'treasure hunt', 'monuments men',
                                              'architect']):
        category = "Artists & Writers"

    # Politicians & Leaders
    elif any(word in overview_lower for word in ['president', 'prime minister', 'governor', 'senator',
                                              'politician', 'election', 'campaign', 'congress', 'parliament',
                                              'fbi agent', 'deep throat', 'watergate']):
        category = "Politicians"

    # Criminals & Outlaws (be more specific - avoid false positives)
    elif any(word in overview_lower for word in ['gangster', 'mob boss', 'mafia', 'drug lord', 'cartel',
                                              'heist', 'robbery', 'outlaw', 'infiltrates']):
        category = "Criminals"

    # Entertainers (Actors, Directors, etc.)
    elif any(word in overview_lower for word in ['actor', 'actress', 'director', 'film producer',
                                              'hollywood', 'performance', 'stage']):
        category = "Entertainers"

    # Military & War (check LAST - many movies mention war but aren't about military figures)
    elif any(word in overview_lower for word in ['soldier', 'general', 'navy', 'marine', 'combat',
                                              'colonel', 'sergeant', 'veteran', 'squadron', 'medic',
                                              'prisoner of war', 'wwii', 'world war']) or \
         ('military' in overview_lower and 'mixed martial' not in overview_lower):
        category = "Military"

    # Historical Events (check for event-focused narratives without specific people)
    elif any(word in title_lower for word in ['disaster', 'attack', 'operation', 'mission', 'incident']) or \
         (('war' in genres_lower or 'history' in genres_lower) and
          not any(person_word in overview_lower[:500] for person_word in ['he ', 'she ', 'his ', 'her ', 'him '])):
        category = "Historical Events"

    return category


def populate_movie_categories(cur, conn, limit=25):
    """
    Populates the MovieCategories table by categorizing movies.
    Uses normalized schema with Categories and MovieCategories tables.
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
    # Get movies that haven't been categorized yet, with their overview and genres
    cur.execute('''
        SELECT
            m.id,
            m.title,
            m.overview,
            GROUP_CONCAT(g.name, ', ') as genre_names
        FROM Movies m
        LEFT JOIN MovieGenres mg ON m.id = mg.movie_id
        LEFT JOIN Genres g ON mg.genre_id = g.id
        WHERE m.id NOT IN (SELECT DISTINCT movie_id FROM MovieCategories)
        AND m.overview IS NOT NULL
        GROUP BY m.id, m.title, m.overview
        LIMIT ?
    ''', (limit,))

    movies_to_process = cur.fetchall()

    if not movies_to_process:
        print("All movies have been categorized!")
        return

    print(f"Categorizing {len(movies_to_process)} movies...")

    for movie_id, title, overview, genre_names in movies_to_process:
        print(f"\nProcessing: {title}")

        # Categorize based on overview and genres
        category_name = categorize_subject_from_overview(title, overview, genre_names)
        print(f"  Category: {category_name}")

        # Get or create category ID
        category_id = insert_or_get_category(cur, conn, category_name)

        # Link movie to category
        cur.execute('''
            INSERT OR IGNORE INTO MovieCategories (movie_id, category_id)
            VALUES (?, ?)
        ''', (movie_id, category_id))

    conn.commit()
    print(f"\n{'='*60}")
    print(f"Successfully categorized {len(movies_to_process)} movies.")

    # Show progress
    cur.execute('SELECT COUNT(DISTINCT movie_id) FROM MovieCategories')
    total_categorized = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Movies WHERE overview IS NOT NULL')
    total_movies = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Categories')
    total_categories = cur.fetchone()[0]
    print(f"Total progress: {total_categorized}/{total_movies} movies categorized.")
    print(f"Total unique categories: {total_categories}")


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

        # Get total count of movies considered
        cur.execute('SELECT COUNT(DISTINCT movie_id) FROM MovieCategories')
        total_movies = cur.fetchone()[0]
        f.write(f"TOTAL MOVIES ANALYZED: {total_movies}\n")
        f.write("="*60 + "\n\n")

        # 1. Count movies by category
        f.write("1. COUNT OF MOVIES BY SUBJECT CATEGORY\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT c.name, COUNT(*) as movie_count
            FROM MovieCategories mc
            JOIN Categories c ON mc.category_id = c.id
            GROUP BY c.name
            ORDER BY movie_count DESC
        ''')

        category_counts = cur.fetchall()
        for category, count in category_counts:
            line = f"{category}: {count} movies\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 2. Category with genre data (JOIN with Genres via MovieGenres and Movies)
        f.write("2. SUBJECT CATEGORIES WITH MOST COMMON MOVIE GENRES\n")
        f.write("-" * 60 + "\n")
        f.write("Note: Movies with multiple genres are counted in each genre bucket separately.\n\n")

        # Get all movies with their categories and genres
        cur.execute('''
            SELECT c.name, g.name
            FROM MovieCategories mc
            JOIN Categories c ON mc.category_id = c.id
            JOIN MovieGenres mg ON mc.movie_id = mg.movie_id
            JOIN Genres g ON mg.genre_id = g.id
        ''')

        all_movie_genres = cur.fetchall()

        # Create a dictionary to count genres by category
        genre_counts = {}

        for category, genre_name in all_movie_genres:
            if category not in genre_counts:
                genre_counts[category] = {}

            if genre_name in genre_counts[category]:
                genre_counts[category][genre_name] += 1
            else:
                genre_counts[category][genre_name] = 1

        # Sort and display results
        for category in sorted(genre_counts.keys()):
            f.write(f"\n{category}:\n")
            print(f"\n{category}:")

            # Sort genres by count (descending) then by name
            sorted_genres = sorted(genre_counts[category].items(),
                                 key=lambda x: (-x[1], x[0]))

            for genre, count in sorted_genres:
                line = f"  {genre}: {count} movies\n"
                f.write(line)
                print(line.strip())

        f.write("\n")

        # 3. Average revenue by subject category (JOIN)
        f.write("3. AVERAGE REVENUE BY SUBJECT CATEGORY (in millions USD)\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT c.name, AVG(m.revenue) / 1000000.0 as avg_revenue_millions, COUNT(*) as movie_count
            FROM MovieCategories mc
            JOIN Categories c ON mc.category_id = c.id
            JOIN Movies m ON mc.movie_id = m.id
            WHERE m.revenue > 0
            GROUP BY c.name
            ORDER BY avg_revenue_millions DESC
        ''')

        revenue_stats = cur.fetchall()
        for category, avg_revenue, movie_count in revenue_stats:
            line = f"{category}: ${avg_revenue:.2f}M (based on {movie_count} movies)\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 4. Revenue by release year (scatterplot data)
        f.write("4. REVENUE BY RELEASE YEAR\n")
        f.write("-" * 60 + "\n")
        f.write("Data for scatterplot showing box office performance over time.\n\n")

        # Get all movies with revenue and release year
        cur.execute('''
            SELECT m.title, CAST(substr(m.release_date, 1, 4) AS INTEGER) as year,
                   m.revenue / 1000000.0 as revenue_millions, c.name
            FROM Movies m
            LEFT JOIN MovieCategories mc ON m.id = mc.movie_id
            LEFT JOIN Categories c ON mc.category_id = c.id
            WHERE m.revenue > 0
            AND m.release_date IS NOT NULL AND m.release_date != ''
            ORDER BY year, revenue_millions DESC
        ''')

        movies_by_year = cur.fetchall()

        if movies_by_year:
            # Group by year for summary statistics
            year_stats = {}
            for title, year, revenue, category in movies_by_year:
                if year not in year_stats:
                    year_stats[year] = {'revenues': [], 'count': 0, 'movies': []}
                year_stats[year]['revenues'].append(revenue)
                year_stats[year]['count'] += 1
                year_stats[year]['movies'].append((title, revenue, category))

            # Display summary by year
            for year in sorted(year_stats.keys()):
                stats = year_stats[year]
                avg_revenue = sum(stats['revenues']) / len(stats['revenues'])
                max_revenue = max(stats['revenues'])

                f.write(f"\n{year}:\n")
                print(f"\n{year}:")

                line = f"  Movies: {stats['count']}\n"
                f.write(line)
                print(line.strip())

                line = f"  Average Revenue: ${avg_revenue:.2f}M\n"
                f.write(line)
                print(line.strip())

                line = f"  Max Revenue: ${max_revenue:.2f}M\n"
                f.write(line)
                print(line.strip())

            # Overall statistics
            all_revenues = [rev for _, _, rev, _ in movies_by_year]
            f.write(f"\nOVERALL STATISTICS:\n")
            f.write(f"  Total movies with revenue data: {len(movies_by_year)}\n")
            f.write(f"  Year range: {min(year_stats.keys())} - {max(year_stats.keys())}\n")
            f.write(f"  Average revenue across all years: ${sum(all_revenues)/len(all_revenues):.2f}M\n")
            f.write(f"  Highest revenue: ${max(all_revenues):.2f}M\n")

            print(f"\nOVERALL STATISTICS:")
            print(f"  Total movies with revenue data: {len(movies_by_year)}")
            print(f"  Year range: {min(year_stats.keys())} - {max(year_stats.keys())}")
            print(f"  Average revenue across all years: ${sum(all_revenues)/len(all_revenues):.2f}M")
            print(f"  Highest revenue: ${max(all_revenues):.2f}M")
        else:
            f.write("No revenue data available.\n")
            print("No revenue data available.")

        f.write("\n" + "="*60 + "\n")
        f.write("END OF CALCULATIONS\n")
        f.write("="*60 + "\n")

    print(f"\n{'='*60}")
    print(f"Calculations saved to: {output_file}")
    print("="*60)


def main():
    cur, conn = set_up_database()
    create_categories_tables(cur, conn)
    populate_movie_categories(cur, conn, limit=25)

    # After all data is collected, run calculations
    cur.execute('SELECT COUNT(DISTINCT movie_id) FROM MovieCategories')
    categorized_count = cur.fetchone()[0]

    if categorized_count > 0:
        print("\nRunning calculations on categorized data...")
        calculate_statistics(cur, conn)
    else:
        print("\nNo categorized data yet. Run this script multiple times to categorize all movies.")

    conn.close()


if __name__ == "__main__":
    main()
