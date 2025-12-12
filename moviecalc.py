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
            category TEXT,
            FOREIGN KEY (movie_id) REFERENCES Movies(id)
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
    str: The category (broad subject type)
    """
    if not plot_summary:
        return "Unknown"

    # Convert to lowercase for easier searching
    plot_lower = plot_summary.lower()
    title_lower = title.lower()
    genres_lower = genres.lower() if genres else ""

    # Category classification based on keywords
    category = "Other"

    # Musicians & Performers
    if any(word in plot_lower for word in ['musician', 'singer', 'vocalist', 'composer', 'band member',
                                            'performs', 'concert', 'album', 'rapper', 'hip hop', 'pianist', 'piano']):
        category = "Musicians"

    # Athletes & Sports
    elif any(word in plot_lower for word in ['boxer', 'boxing', 'football', 'basketball', 'baseball',
                                              'olympic', 'race car', 'racing driver', 'quarterback', 'athlete',
                                              'coach', 'sport']):
        category = "Athletes"

    # Criminals & Outlaws
    elif any(word in plot_lower for word in ['criminal', 'gangster', 'murder', 'killer', 'mob',
                                              'mafia', 'drug', 'cartel', 'prison', 'fbi', 'arrest',
                                              'crime', 'heist', 'robbery', 'outlaw']):
        category = "Criminals"

    # Military & War
    elif any(word in plot_lower for word in ['military', 'soldier', 'general', 'war', 'battle',
                                              'army', 'navy', 'marine', 'combat', 'troop', 'officer',
                                              'colonel', 'sergeant', 'veteran', 'squadron']):
        category = "Military"

    # Businesspeople & Entrepreneurs
    elif any(word in plot_lower for word in ['entrepreneur', 'ceo', 'founder', 'billionaire',
                                              'creates a company', 'starts a business', 'facebook', 'zuckerberg']):
        category = "Businesspeople"

    # Scientists & Academics
    elif any(word in plot_lower for word in ['scientist', 'mathematician', 'physicist', 'professor',
                                              'researcher', 'theory', 'discover', 'invention', 'academic']):
        category = "Scientists"

    # Activists & Social Figures
    elif any(word in plot_lower for word in ['activist', 'civil rights', 'protest', 'movement',
                                              'rights', 'equality', 'discrimination', 'segregation']):
        category = "Activists"

    # Politicians & Leaders
    elif any(word in plot_lower for word in ['president', 'prime minister', 'governor', 'senator',
                                              'politician', 'election', 'campaign', 'congress', 'parliament']):
        category = "Politicians"

    # Artists & Writers
    elif any(word in plot_lower for word in ['artist', 'painter', 'writer', 'author', 'novel',
                                              'book', 'journalist', 'reporter', 'paint', 'artwork']):
        category = "Artists & Writers"

    # Entertainers (Actors, Directors, etc.)
    elif any(word in plot_lower for word in ['actor', 'actress', 'director', 'film', 'movie',
                                              'hollywood', 'performance', 'stage']):
        category = "Entertainers"

    # Historical Events (check for event-focused narratives)
    elif any(word in title_lower for word in ['disaster', 'attack', 'operation', 'mission', 'incident']) or \
         (('war' in genres_lower or 'history' in genres_lower) and
          not any(person_word in plot_lower[:500] for person_word in ['he ', 'she ', 'his ', 'her ', 'him '])):
        category = "Historical Events"

    return category


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
    # Get movies that haven't been categorized yet, along with their plot summaries and genres
    cur.execute('''
        SELECT m.id, m.title, p.plot_summary, td.genres
        FROM Movies m
        JOIN Plots p ON m.id = p.movie_id
        LEFT JOIN TMDB_Data td ON m.id = td.movie_id
        WHERE m.id NOT IN (SELECT movie_id FROM Subject_Categories)
        AND p.plot_summary IS NOT NULL
        LIMIT ?
    ''', (limit,))

    movies_to_process = cur.fetchall()

    if not movies_to_process:
        print("All movies have been categorized!")
        return

    print(f"Categorizing {len(movies_to_process)} movies...")

    for movie_id, title, plot_summary, genres in movies_to_process:
        print(f"\nProcessing: {title}")

        # Categorize based on plot summary and genres
        category = categorize_subject_from_plot(title, plot_summary, genres)
        print(f"  Category: {category}")

        # Store in database
        cur.execute('''
            INSERT OR REPLACE INTO Subject_Categories
            (movie_id, category)
            VALUES (?, ?)
        ''', (movie_id, category))

    conn.commit()
    print(f"\n{'='*60}")
    print(f"Successfully categorized {len(movies_to_process)} movies.")

    # Show progress
    cur.execute('SELECT COUNT(*) FROM Subject_Categories')
    total_categorized = cur.fetchone()[0]
    cur.execute('SELECT COUNT(*) FROM Movies m JOIN Plots p ON m.id = p.movie_id WHERE p.plot_summary IS NOT NULL')
    total_movies = cur.fetchone()[0]
    print(f"Total progress: {total_categorized}/{total_movies} movies categorized.")


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
        cur.execute('SELECT COUNT(*) FROM Subject_Categories')
        total_movies = cur.fetchone()[0]
        f.write(f"TOTAL MOVIES ANALYZED: {total_movies}\n")
        f.write("="*60 + "\n\n")

        # 1. Count movies by category
        f.write("1. COUNT OF MOVIES BY SUBJECT CATEGORY\n")
        f.write("-" * 60 + "\n")

        cur.execute('''
            SELECT sc.category, COUNT(*) as movie_count
            FROM Subject_Categories sc
            GROUP BY sc.category
            ORDER BY movie_count DESC
        ''')

        category_counts = cur.fetchall()
        for category, count in category_counts:
            line = f"{category}: {count} movies\n"
            f.write(line)
            print(line.strip())

        f.write("\n")

        # 2. Category with genre data (JOIN with TMDB_Data and Movies)
        # Note: Movies may be counted in multiple genre buckets
        f.write("2. SUBJECT CATEGORIES WITH MOST COMMON MOVIE GENRES\n")
        f.write("-" * 60 + "\n")
        f.write("Note: Movies with multiple genres are counted in each genre bucket separately.\n\n")

        # Get all movies with their categories and genres
        cur.execute('''
            SELECT sc.category, td.genres
            FROM Subject_Categories sc
            JOIN TMDB_Data td ON sc.movie_id = td.movie_id
            WHERE td.genres IS NOT NULL AND td.genres != ''
        ''')

        all_movies = cur.fetchall()

        # Create a dictionary to count genres by category
        genre_counts = {}

        for category, genres_str in all_movies:
            # Split genres by comma and strip whitespace
            individual_genres = [g.strip() for g in genres_str.split(',')]

            if category not in genre_counts:
                genre_counts[category] = {}

            # Count each genre separately
            for genre in individual_genres:
                if genre in genre_counts[category]:
                    genre_counts[category][genre] += 1
                else:
                    genre_counts[category][genre] = 1

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
            SELECT sc.category, AVG(td.revenue) / 1000000.0 as avg_revenue_millions, COUNT(*) as movie_count
            FROM Subject_Categories sc
            JOIN TMDB_Data td ON sc.movie_id = td.movie_id
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

        # 4. Revenue by release year (scatterplot data)
        f.write("4. REVENUE BY RELEASE YEAR\n")
        f.write("-" * 60 + "\n")
        f.write("Data for scatterplot showing box office performance over time.\n\n")

        # Get all movies with revenue and release year
        cur.execute('''
            SELECT m.title, CAST(substr(td.release_date, 1, 4) AS INTEGER) as year,
                   td.revenue / 1000000.0 as revenue_millions, sc.category
            FROM TMDB_Data td
            JOIN Movies m ON td.movie_id = m.id
            LEFT JOIN Subject_Categories sc ON m.id = sc.movie_id
            WHERE td.revenue > 0
            AND td.release_date IS NOT NULL AND td.release_date != ''
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

                # List top 3 movies for that year
                f.write("  Top movies:\n")
                print("  Top movies:")
                top_movies = sorted(stats['movies'], key=lambda x: -x[1])[:3]
                for movie_title, revenue, category in top_movies:
                    cat_str = f" ({category})" if category else ""
                    line = f"    - {movie_title}: ${revenue:.2f}M{cat_str}\n"
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
