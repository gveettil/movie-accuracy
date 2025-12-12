import sqlite3
import os
import matplotlib.pyplot as plt
import numpy as np

def set_up_database():
    """Sets up a SQLite database connection and cursor."""
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path + "/movies.db")
    cur = conn.cursor()
    return cur, conn


def create_visualization_1(cur):
    """
    Visualization 1: Bar chart of movie counts by subject category.
    """
    print("Creating Visualization 1: Movie Count by Subject Category")

    cur.execute('''
        SELECT sc.category, COUNT(*) as movie_count
        FROM Subject_Categories sc
        GROUP BY sc.category
        ORDER BY movie_count DESC
    ''')

    data = cur.fetchall()
    categories = [row[0] for row in data]
    counts = [row[1] for row in data]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(categories, counts)
    plt.xlabel('Subject Category')
    plt.ylabel('Number of Movies')
    plt.title('Count of Movies by Subject Category')
    plt.xticks(rotation=45, ha='right')

    # Add movie count annotations on bars
    for bar, count in zip(bars, counts):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'n={count}',
                ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visualization_1_category_counts.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def create_visualization_2(cur):
    """
    Visualization 2: Stacked bar chart showing top genres for each subject category.
    """
    print("Creating Visualization 2: Genre Distribution by Subject Category")

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
        individual_genres = [g.strip() for g in genres_str.split(',')]

        if category not in genre_counts:
            genre_counts[category] = {}

        for genre in individual_genres:
            if genre in genre_counts[category]:
                genre_counts[category][genre] += 1
            else:
                genre_counts[category][genre] = 1

    # Get top 5 genres overall to focus on
    all_genres_flat = {}
    for category_genres in genre_counts.values():
        for genre, count in category_genres.items():
            all_genres_flat[genre] = all_genres_flat.get(genre, 0) + count

    top_genres = sorted(all_genres_flat.items(), key=lambda x: -x[1])[:6]
    top_genre_names = [g[0] for g in top_genres]

    # Sort categories by total movie count
    category_totals = [(cat, sum(genre_counts[cat].values())) for cat in genre_counts.keys()]
    category_totals.sort(key=lambda x: -x[1])
    sorted_categories = [cat[0] for cat in category_totals]

    # Prepare data for stacked bar chart
    data_for_plot = {genre: [] for genre in top_genre_names}

    for category in sorted_categories:
        for genre in top_genre_names:
            count = genre_counts[category].get(genre, 0)
            data_for_plot[genre].append(count)

    # Create stacked bar chart
    plt.figure(figsize=(12, 7))

    x = np.arange(len(sorted_categories))
    width = 0.6
    bottom = np.zeros(len(sorted_categories))

    for genre in top_genre_names:
        plt.bar(x, data_for_plot[genre], width, label=genre, bottom=bottom)
        bottom += np.array(data_for_plot[genre])

    # Add total count annotations on top of stacked bars
    for i, total in enumerate(bottom):
        plt.text(x[i], total,
                f'n={int(total)}',
                ha='center', va='bottom', fontsize=8)

    plt.xlabel('Subject Category')
    plt.ylabel('Number of Movies')
    plt.title('Top Genre Distribution by Subject Category')
    plt.xticks(x, sorted_categories, rotation=45, ha='right')
    plt.legend(title='Genre', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visualization_2_genre_by_category.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def create_visualization_3(cur):
    """
    Visualization 3: Bar chart of average revenue by subject category.
    """
    print("Creating Visualization 3: Average Revenue by Subject Category")

    cur.execute('''
        SELECT sc.category, AVG(td.revenue) / 1000000.0 as avg_revenue_millions, COUNT(*) as movie_count
        FROM Subject_Categories sc
        JOIN TMDB_Data td ON sc.movie_id = td.movie_id
        WHERE td.revenue > 0
        GROUP BY sc.category
        ORDER BY avg_revenue_millions DESC
    ''')

    data = cur.fetchall()
    categories = [row[0] for row in data]
    revenues = [row[1] for row in data]
    movie_counts = [row[2] for row in data]

    plt.figure(figsize=(10, 6))
    bars = plt.bar(categories, revenues)
    plt.xlabel('Subject Category')
    plt.ylabel('Average Revenue (Millions USD)')
    plt.title('Average Revenue by Subject Category')
    plt.xticks(rotation=45, ha='right')

    # Add movie count annotations on bars
    for i, (bar, count) in enumerate(zip(bars, movie_counts)):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height,
                f'n={count}',
                ha='center', va='bottom', fontsize=8)

    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visualization_3_avg_revenue.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def create_visualization_4(cur):
    """
    Visualization 4: Bar chart showing genre distribution by decade.
    """
    print("Creating Visualization 4: Genre Distribution by Decade")

    # Get all movies with their genres and release years
    cur.execute('''
        SELECT td.genres, CAST(substr(td.release_date, 1, 4) AS INTEGER) as year
        FROM TMDB_Data td
        WHERE td.genres IS NOT NULL AND td.genres != ''
        AND td.release_date IS NOT NULL AND td.release_date != ''
        ORDER BY year
    ''')

    all_movies_by_year = cur.fetchall()

    # Create a dictionary to count genres by decade
    genre_by_decade = {}

    for genres_str, year in all_movies_by_year:
        # Calculate decade (e.g., 2015 -> 2010s)
        decade = (year // 10) * 10

        individual_genres = [g.strip() for g in genres_str.split(',')]

        if decade not in genre_by_decade:
            genre_by_decade[decade] = {}

        for genre in individual_genres:
            if genre in genre_by_decade[decade]:
                genre_by_decade[decade][genre] += 1
            else:
                genre_by_decade[decade][genre] = 1

    # Get top genres to plot (to avoid clutter)
    all_genres_flat = {}
    for decade_genres in genre_by_decade.values():
        for genre, count in decade_genres.items():
            all_genres_flat[genre] = all_genres_flat.get(genre, 0) + count

    top_genres = sorted(all_genres_flat.items(), key=lambda x: -x[1])[:8]
    top_genre_names = [g[0] for g in top_genres]

    # Prepare data for grouped bar chart
    plt.figure(figsize=(14, 8))

    sorted_decades = sorted(genre_by_decade.keys())
    decade_labels = [f"{d}s" for d in sorted_decades]

    x = np.arange(len(sorted_decades))
    width = 0.1  # width of each bar

    # Get matplotlib default color cycle
    prop_cycle = plt.rcParams['axes.prop_cycle']
    colors = prop_cycle.by_key()['color']

    for idx, genre in enumerate(top_genre_names):
        counts = []
        for decade in sorted_decades:
            count = genre_by_decade[decade].get(genre, 0)
            counts.append(count)

        # Position bars for each genre
        offset = width * (idx - len(top_genre_names) / 2)
        color = colors[idx % len(colors)]
        plt.bar(x + offset, counts, width, label=genre, color=color, alpha=0.8)

    plt.xlabel('Decade')
    plt.ylabel('Number of Movies')
    plt.title('Genre Distribution by Decade (Top 8 Genres)')
    plt.xticks(x, decade_labels)
    plt.legend(title='Genre', bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visualization_4_genre_by_decade.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")
    plt.close()


def main():
    print("="*60)
    print("CREATING VISUALIZATIONS FOR MOVIE DATA")
    print("="*60 + "\n")

    cur, conn = set_up_database()

    try:
        create_visualization_1(cur)
        print()
        create_visualization_2(cur)
        print()
        create_visualization_3(cur)
        print()
        create_visualization_4(cur)

        print("\n" + "="*60)
        print("ALL VISUALIZATIONS CREATED SUCCESSFULLY!")
        print("="*60)

    except Exception as e:
        print(f"Error creating visualizations: {e}")
        import traceback
        traceback.print_exc()

    finally:
        conn.close()


if __name__ == "__main__":
    main()
