import os
import html
import math
import requests
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURATION
# ============================================================

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]

GITHUB_USERNAME = os.environ.get(
    "GITHUB_USERNAME",
    "BekkamMallishwari"
)

INDIA_TZ = ZoneInfo("Asia/Kolkata")

OUTPUT_FILE = "github-metrics.svg"


# ============================================================
# CURRENT MONTH
# ============================================================

today = datetime.now(INDIA_TZ).date()

# First day of current month
start_date = today.replace(day=1)

# First day of next month
if start_date.month == 12:
    next_month = date(
        start_date.year + 1,
        1,
        1
    )
else:
    next_month = date(
        start_date.year,
        start_date.month + 1,
        1
    )

# Last day of current month
end_date = next_month - timedelta(days=1)


# ============================================================
# GITHUB GRAPHQL QUERY
# ============================================================

query = """
query($username: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $username) {
    contributionsCollection(
      from: $from
      to: $to
    ) {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


from_datetime = (
    f"{start_date}T00:00:00+05:30"
)

to_datetime = (
    f"{end_date}T23:59:59+05:30"
)


# ============================================================
# GITHUB API REQUEST
# ============================================================

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Content-Type": "application/json",
}

variables = {
    "username": GITHUB_USERNAME,
    "from": from_datetime,
    "to": to_datetime,
}


response = requests.post(
    "https://api.github.com/graphql",
    json={
        "query": query,
        "variables": variables,
    },
    headers=headers,
    timeout=30,
)

response.raise_for_status()

result = response.json()


# ============================================================
# GRAPHQL ERROR CHECK
# ============================================================

if "errors" in result:
    raise RuntimeError(result["errors"])


# ============================================================
# USER CHECK
# ============================================================

user_data = result["data"]["user"]

if user_data is None:
    raise RuntimeError(
        f"GitHub user not found: {GITHUB_USERNAME}"
    )


calendar = (
    user_data["contributionsCollection"]
    ["contributionCalendar"]
)


# ============================================================
# BUILD DAILY CONTRIBUTION MAP
# ============================================================

contribution_map = {}

for week in calendar["weeks"]:

    for day_data in week["contributionDays"]:

        contribution_map[
            day_data["date"]
        ] = day_data["contributionCount"]


# ============================================================
# CREATE FULL MONTH DATA
# ============================================================

# IMPORTANT:
# We create ALL days of the month here.
#
# Example:
# October -> 31 days
# November -> 30 days
# December -> 31 days
#
# Future days remain None instead of 0.

dates = []
counts = []

current = start_date

while current <= end_date:

    dates.append(current)

    # Only use actual GitHub data up to today.
    if current <= today:

        counts.append(
            contribution_map.get(
                current.isoformat(),
                0
            )
        )

    else:

        # Future date = no data yet
        counts.append(None)

    current += timedelta(days=1)


# ============================================================
# ACTUAL CONTRIBUTION VALUES
# ============================================================

actual_counts = [
    value
    for value in counts
    if value is not None
]


# Total contributions completed so far
total_contributions = sum(actual_counts)


# Highest number of contributions on one day
max_count = (
    max(actual_counts)
    if actual_counts
    else 0
)


# ============================================================
# GRAPH DIMENSIONS
# ============================================================

WIDTH = 1100
HEIGHT = 450

LEFT = 80
RIGHT = 40

TOP = 75
BOTTOM = 365

GRAPH_WIDTH = WIDTH - LEFT - RIGHT
GRAPH_HEIGHT = BOTTOM - TOP


# ============================================================
# DYNAMIC Y-AXIS
# ============================================================

def calculate_y_scale(maximum):
    """
    Creates a clean Y-axis based on the
    user's actual contribution count.

    Examples:

    max = 10
    -> 0, 2, 4, 6, 8, 10

    max = 23
    -> 0, 5, 10, 15, 20, 25

    max = 47
    -> 0, 10, 20, 30, 40, 50
    """

    if maximum <= 0:
        return 5, 1

    # Small values
    if maximum <= 5:
        return 5, 1

    if maximum <= 10:
        return 10, 2

    if maximum <= 20:
        return 20, 4

    if maximum <= 25:
        return 25, 5

    if maximum <= 50:
        return 50, 10

    if maximum <= 100:
        return 100, 20

    # Larger values
    magnitude = 10 ** math.floor(
        math.log10(maximum)
    )

    normalized = maximum / magnitude

    if normalized <= 1:
        nice = 1
    elif normalized <= 2:
        nice = 2
    elif normalized <= 5:
        nice = 5
    else:
        nice = 10

    y_maximum = int(
        nice * magnitude
    )

    y_step = y_maximum / 5

    return (
        y_maximum,
        y_step
    )


y_max, y_step = calculate_y_scale(
    max_count
)


# ============================================================
# COORDINATE FUNCTIONS
# ============================================================

def x_position(index):

    # IMPORTANT:
    # X positions use the FULL MONTH.
    #
    # Therefore:
    # October 1 -> left
    # October 31 -> right

    if len(dates) <= 1:
        return LEFT

    return (
        LEFT
        + (
            index / (len(dates) - 1)
        ) * GRAPH_WIDTH
    )


def y_position(value):

    return (
        BOTTOM
        - (
            value / y_max
        ) * GRAPH_HEIGHT
    )


# ============================================================
# CREATE ACTUAL GRAPH POINTS
# ============================================================

points = []

for index, count in enumerate(counts):

    # Don't create points for future days
    if count is None:
        continue

    x = x_position(index)

    y = y_position(count)

    points.append(
        (
            x,
            y,
            count,
            dates[index]
        )
    )


# ============================================================
# SVG ESCAPE
# ============================================================

def escape(value):
    return html.escape(str(value))


# ============================================================
# TITLE
# ============================================================

month_name = start_date.strftime("%B")

year = start_date.year

title = (
    "Mallishwari's Contribution Graph"
)

subtitle = (
    f"{month_name} {year} • "
    f"{total_contributions} contributions"
)


# ============================================================
# START SVG
# ============================================================

svg = f'''<svg
    xmlns="http://www.w3.org/2000/svg"
    width="{WIDTH}"
    height="{HEIGHT}"
    viewBox="0 0 {WIDTH} {HEIGHT}"
>

<!-- Background -->

<rect
    width="{WIDTH}"
    height="{HEIGHT}"
    rx="8"
    fill="#0d1117"
/>


<!-- =====================================================
     TITLE
===================================================== -->

<text
    x="{WIDTH / 2}"
    y="32"
    text-anchor="middle"
    fill="#ffffff"
    font-size="17"
    font-family="Arial, Helvetica, sans-serif"
    font-weight="bold"
>
    {escape(title)}
</text>


<!-- Subtitle -->

<text
    x="{WIDTH / 2}"
    y="52"
    text-anchor="middle"
    fill="#8b949e"
    font-size="12"
    font-family="Arial, Helvetica, sans-serif"
>
    {escape(subtitle)}
</text>


<!-- =====================================================
     GRAPH BORDER
===================================================== -->

<rect
    x="{LEFT}"
    y="{TOP}"
    width="{GRAPH_WIDTH}"
    height="{GRAPH_HEIGHT}"
    fill="none"
    stroke="#30363d"
    stroke-width="1"
/>
'''


# ============================================================
# Y-AXIS GRID
# ============================================================

number_of_ticks = int(
    round(y_max / y_step)
)

for i in range(
    number_of_ticks + 1
):

    value = i * y_step

    y = y_position(value)

    svg += f'''
    <line
        x1="{LEFT}"
        y1="{y:.2f}"
        x2="{WIDTH - RIGHT}"
        y2="{y:.2f}"
        stroke="#30363d"
        stroke-width="1"
    />

    <text
        x="{LEFT - 12}"
        y="{y + 4:.2f}"
        text-anchor="end"
        fill="#8b949e"
        font-size="11"
        font-family="Arial, Helvetica, sans-serif"
    >
        {value:.0f}
    </text>
    '''


# ============================================================
# X-AXIS — ALL DAYS OF THE MONTH
# ============================================================

for index, current_date in enumerate(dates):

    x = x_position(index)

    # Vertical grid for every day
    svg += f'''
    <line
        x1="{x:.2f}"
        y1="{TOP}"
        x2="{x:.2f}"
        y2="{BOTTOM}"
        stroke="#21262d"
        stroke-width="1"
    />
    '''

    # Show every day number
    svg += f'''
    <text
        x="{x:.2f}"
        y="{BOTTOM + 20}"
        text-anchor="middle"
        fill="#8b949e"
        font-size="9"
        font-family="Arial, Helvetica, sans-serif"
    >
        {current_date.day}
    </text>
    '''


# ============================================================
# AREA UNDER GRAPH
# ============================================================

if len(points) >= 2:

    area_points = [
        f"{x:.2f},{y:.2f}"
        for x, y, _, _ in points
    ]

    first_x = points[0][0]

    last_x = points[-1][0]

    # Bottom-left
    area_points.insert(
        0,
        f"{first_x:.2f},{BOTTOM}"
    )

    # Bottom-right
    area_points.append(
        f"{last_x:.2f},{BOTTOM}"
    )

    svg += f'''
    <polygon
        points="{" ".join(area_points)}"
        fill="#238636"
        fill-opacity="0.25"
    />
    '''


# ============================================================
# GREEN CONTRIBUTION LINE
# ============================================================

if len(points) >= 2:

    line_points = " ".join(
        f"{x:.2f},{y:.2f}"
        for x, y, _, _ in points
    )

    svg += f'''
    <polyline
        points="{line_points}"
        fill="none"
        stroke="#39d353"
        stroke-width="3"
        stroke-linejoin="round"
        stroke-linecap="round"
    />
    '''


# ============================================================
# DATA POINTS
# ============================================================

for (
    x,
    y,
    count,
    contribution_date
) in points:

    date_text = contribution_date.strftime(
        "%b %d"
    )

    contribution_word = (
        "contribution"
        if count == 1
        else "contributions"
    )

    svg += f'''
    <circle
        cx="{x:.2f}"
        cy="{y:.2f}"
        r="4"
        fill="#39d353"
        stroke="#0d1117"
        stroke-width="2"
    >
        <title>
            {escape(date_text)}: {count} {contribution_word}
        </title>
    </circle>
    '''


# ============================================================
# AXIS TITLES
# ============================================================

svg += f'''
<!-- X Axis -->

<text
    x="{WIDTH / 2}"
    y="{HEIGHT - 15}"
    text-anchor="middle"
    fill="#8b949e"
    font-size="12"
    font-family="Arial, Helvetica, sans-serif"
>
    Date
</text>


<!-- Y Axis -->

<text
    x="18"
    y="{TOP + GRAPH_HEIGHT / 2}"
    text-anchor="middle"
    fill="#8b949e"
    font-size="12"
    font-family="Arial, Helvetica, sans-serif"
    transform="rotate(-90 18 {TOP + GRAPH_HEIGHT / 2})"
>
    Contributions
</text>


</svg>
'''


# ============================================================
# SAVE SVG
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    file.write(svg)


# ============================================================
# ACTIONS LOG
# ============================================================

print("==========================================")
print("Contribution graph generated successfully")
print("==========================================")

print(f"User: {GITHUB_USERNAME}")

print(
    f"Month: {month_name} {year}"
)

print(
    f"Total contributions so far: "
    f"{total_contributions}"
)

print(
    f"Days in month: "
    f"{len(dates)}"
)

print(
    f"Days with data: "
    f"{len(points)}"
)

print(
    f"Highest daily contributions: "
    f"{max_count}"
)

print(
    f"Y-axis maximum: "
    f"{y_max}"
)

print(
    f"Y-axis step: "
    f"{y_step}"
)

print(
    f"Output: {OUTPUT_FILE}"
)
