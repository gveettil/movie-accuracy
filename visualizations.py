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
    Visualization 4: Line plot of average revenue by release year.
    """
    print("Creating Visualization 4: Average Revenue by Release Year")

    # Get average revenue by year
    cur.execute('''
        SELECT CAST(substr(td.release_date, 1, 4) AS INTEGER) as year,
               AVG(td.revenue) / 1000000.0 as avg_revenue_millions,
               COUNT(*) as movie_count
        FROM TMDB_Data td
        WHERE td.revenue > 0
        AND td.release_date IS NOT NULL AND td.release_date != ''
        GROUP BY year
        ORDER BY year
    ''')

    data = cur.fetchall()
    years = [row[0] for row in data]
    avg_revenues = [row[1] for row in data]
    movie_counts = [row[2] for row in data]

    # Create line plot
    plt.figure(figsize=(12, 7))
    plt.plot(years, avg_revenues, marker='o', linewidth=2, markersize=6)

    plt.xlabel('Release Year')
    plt.ylabel('Average Revenue (Millions USD)')
    plt.title('Average Box Office Revenue by Release Year')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'visualization_4_revenue_by_year.png')
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
