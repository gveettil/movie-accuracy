import sqlite3
import os
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


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


def visualize_category_distribution(cur):
    """
    Creates a horizontal bar chart showing the distribution of movies by subject category.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    """
    print("\nCreating Visualization 1: Category Distribution...")

    # Get category counts
    cur.execute('''
        SELECT sc.category, COUNT(*) as movie_count
        FROM Subject_Categories sc
        GROUP BY sc.category
        ORDER BY movie_count DESC
    ''')

    data = cur.fetchall()
    categories = [row[0] for row in data]
    counts = [row[1] for row in data]

    # Create horizontal bar chart with custom colors
    fig, ax = plt.subplots(figsize=(12, 8))

    # Color palette - different from basic matplotlib defaults
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8',
              '#F7DC6F', '#BB8FCE', '#85C1E2', '#F8B739', '#52B788']

    bars = ax.barh(categories, counts, color=colors[:len(categories)], edgecolor='black', linewidth=1.2)

    # Add value labels on the bars
    for i, (bar, count) in enumerate(zip(bars, counts)):
        ax.text(count + 0.5, i, str(count), va='center', fontweight='bold', fontsize=10)

    ax.set_xlabel('Number of Movies', fontsize=14, fontweight='bold')
    ax.set_ylabel('Subject Category', fontsize=14, fontweight='bold')
    ax.set_title('Distribution of True Story Movies by Subject Category',
                 fontsize=16, fontweight='bold', pad=20)
    ax.grid(axis='x', alpha=0.3, linestyle='--')

    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'category_distribution.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved to: {output_path}")
    plt.close()


def visualize_people_vs_events(cur):
    """
    Creates a pie chart showing movies about people vs events/books.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    """
    print("\nCreating Visualization 2: People vs Events/Books...")

    # Get person vs non-person counts
    cur.execute('''
        SELECT
            CASE WHEN is_person = 1 THEN 'About People' ELSE 'About Events/Books' END as type,
            COUNT(*) as count
        FROM Subject_Categories
        GROUP BY is_person
    ''')

    data = cur.fetchall()
    labels = [row[0] for row in data]
    sizes = [row[1] for row in data]

    # Create pie chart with custom styling
    fig, ax = plt.subplots(figsize=(10, 8))

    # Custom colors (not basic red/blue)
    colors = ['#FF8C94', '#9DB4C0']
    explode = (0.05, 0)  # Explode the first slice

    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors,
                                        autopct='%1.1f%%', startangle=90, textprops={'fontsize': 12},
                                        wedgeprops={'edgecolor': 'black', 'linewidth': 2})

    # Make percentage text bold and white
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')
        autotext.set_fontsize(14)

    # Make labels bold
    for text in texts:
        text.set_fontweight('bold')
        text.set_fontsize(13)

    ax.set_title('True Story Movies: People vs Events/Books',
                 fontsize=16, fontweight='bold', pad=20)

    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'people_vs_events.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved to: {output_path}")
    plt.close()


def visualize_top_occupations(cur):
    """
    Creates a vertical bar chart showing the top 10 occupations in true story movies.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    """
    print("\nCreating Visualization 3: Top 10 Occupations...")

    # Get top 10 occupations
    cur.execute('''
        SELECT occupation, COUNT(*) as count
        FROM Subject_Categories
        WHERE occupation IS NOT NULL
        GROUP BY occupation
        ORDER BY count DESC
        LIMIT 10
    ''')

    data = cur.fetchall()
    occupations = [row[0] for row in data]
    counts = [row[1] for row in data]

    # Create vertical bar chart with gradient-like colors
    fig, ax = plt.subplots(figsize=(14, 8))

    # Create color gradient from dark to light
    colors = plt.cm.viridis([i/len(occupations) for i in range(len(occupations))])

    bars = ax.bar(range(len(occupations)), counts, color=colors, edgecolor='black', linewidth=1.5)

    # Add value labels on top of bars
    for i, (bar, count) in enumerate(zip(bars, counts)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.3,
                f'{count}', ha='center', va='bottom', fontweight='bold', fontsize=11)

    ax.set_xticks(range(len(occupations)))
    ax.set_xticklabels(occupations, rotation=45, ha='right', fontsize=11)
    ax.set_ylabel('Number of Movies', fontsize=14, fontweight='bold')
    ax.set_xlabel('Occupation', fontsize=14, fontweight='bold')
    ax.set_title('Top 10 Occupations Featured in True Story Movies',
                 fontsize=16, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'top_occupations.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved to: {output_path}")
    plt.close()


def visualize_revenue_by_category(cur):
    """
    Creates a bar chart showing average revenue by subject category.
    BONUS VISUALIZATION.

    Parameters
    -----------------------
    cur: Cursor
        The database cursor.
    """
    print("\nCreating Bonus Visualization: Average Revenue by Category...")

    # Get average revenue by category
    cur.execute('''
        SELECT sc.category, AVG(td.revenue) / 1000000.0 as avg_revenue_millions
        FROM Subject_Categories sc
        JOIN True_Story_Movies tsm ON sc.movie_id = tsm.id
        JOIN Movies m ON tsm.title = m.title
        JOIN TMDB_Data td ON m.id = td.movie_id
        WHERE td.revenue > 0
        GROUP BY sc.category
        ORDER BY avg_revenue_millions DESC
    ''')

    data = cur.fetchall()
    if not data:
        print("  No revenue data available for visualization.")
        return

    categories = [row[0] for row in data]
    revenues = [row[1] for row in data]

    # Create bar chart
    fig, ax = plt.subplots(figsize=(12, 8))

    # Custom color scheme (orange to red gradient)
    colors = plt.cm.YlOrRd([0.3 + 0.7 * i/len(categories) for i in range(len(categories))])

    bars = ax.bar(range(len(categories)), revenues, color=colors, edgecolor='black', linewidth=1.5)

    # Add value labels
    for i, (bar, revenue) in enumerate(zip(bars, revenues)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'${revenue:.1f}M', ha='center', va='bottom', fontweight='bold', fontsize=10)

    ax.set_xticks(range(len(categories)))
    ax.set_xticklabels(categories, rotation=45, ha='right', fontsize=11)
    ax.set_ylabel('Average Revenue (Millions USD)', fontsize=14, fontweight='bold')
    ax.set_xlabel('Subject Category', fontsize=14, fontweight='bold')
    ax.set_title('Average Box Office Revenue by Subject Category',
                 fontsize=16, fontweight='bold', pad=20)
    ax.grid(axis='y', alpha=0.3, linestyle='--')

    plt.tight_layout()
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'revenue_by_category.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"  Saved to: {output_path}")
    plt.close()


def main():
    """
    Main function to create all visualizations.
    """
    print("="*60)
    print("CREATING VISUALIZATIONS")
    print("="*60)

    cur, conn = set_up_database()

    # Check if we have data to visualize
    cur.execute('SELECT COUNT(*) FROM Subject_Categories')
    count = cur.fetchone()[0]

    if count == 0:
        print("\nNo data available for visualization.")
        print("Please run moviecalc.py multiple times to categorize subjects first.")
        conn.close()
        return

    print(f"\nFound {count} categorized subjects. Creating visualizations...")

    # Create visualizations
    visualize_category_distribution(cur)
    visualize_people_vs_events(cur)
    visualize_top_occupations(cur)
    visualize_revenue_by_category(cur)

    conn.close()

    print("\n" + "="*60)
    print("ALL VISUALIZATIONS COMPLETE!")
    print("="*60)


if __name__ == "__main__":
    main()
