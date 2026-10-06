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

# Don't show future days as zero.
# The graph stops at today's date.
plot_end = min(today, end_date)


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


# GitHub contribution dates in India time
from_datetime = f"{start_date}T00:00:00+05:30"
to_datetime = f"{end_date}T23:59:59+05:30"


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


# Check HTTP error
response.raise_for_status()

result = response.json()


# Check GraphQL errors
if "errors" in result:
    raise RuntimeError(result["errors"])


# Check user
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


# Calculate monthly total ourselves.
# GitHub does not provide totalContributions
# directly on ContributionsCollection.
total_contributions = sum(
    contribution_map.values()
)


# ============================================================
# CREATE DATE + CONTRIBUTION LIST
# ============================================================

dates = []
counts = []

current = start_date

while current <= plot_end:

    dates.append(current)

    counts.append(
        contribution_map.get(
            current.isoformat(),
            0
        )
    )

    current += timedelta(days=1)


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
# Y-AXIS SCALE
# ============================================================

max_count = max(counts) if counts else 0


def nice_maximum(value):
    """
    Convert the maximum contribution value
    into a clean graph scale.

    Examples:

    7   -> 10
    18  -> 20
    37  -> 50
    83  -> 100
    """

    if value <= 0:
        return 5

    magnitude = 10 ** math.floor(
        math.log10(value)
    )

    normalized = value / magnitude

    if normalized <= 1:
        nice = 1

    elif normalized <= 2:
        nice = 2

    elif normalized <= 5:
        nice = 5

    else:
        nice = 10

    return int(nice * magnitude)


y_max = nice_maximum(max_count)

# Minimum graph height
if y_max < 5:
    y_max = 5


# ============================================================
# COORDINATE FUNCTIONS
# ============================================================

def x_position(index):

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
# CREATE GRAPH POINTS
# ============================================================

points = []

for index, count in enumerate(counts):

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
# SVG HELPER
# ============================================================

def escape(value):
    return html.escape(str(value))


# ============================================================
# TITLE
# ============================================================

month_name = start_date.strftime("%B")
year = start_date.year

title = "Mallishwari's Contribution Graph"

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


<!-- ======================================================
     TITLE
====================================================== -->

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


<!-- ======================================================
     GRAPH BORDER
====================================================== -->

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
# HORIZONTAL GRID LINES
# ============================================================

TICK_COUNT = 5

for i in range(TICK_COUNT + 1):

    value = (
        y_max * i / TICK_COUNT
    )

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
# X-AXIS LABEL POSITIONS
# ============================================================

# Around 8 labels across the graph

label_count = min(
    8,
    len(dates)
)

label_indices = []

if label_count > 1:

    for i in range(label_count):

        index = round(
            i
            * (len(dates) - 1)
            / (label_count - 1)
        )

        if index not in label_indices:
            label_indices.append(index)

else:

    label_indices = [0]


# ============================================================
# VERTICAL GRID LINES
# ============================================================

for index in label_indices:

    x = x_position(index)

    svg += f'''
    <line
        x1="{x:.2f}"
        y1="{TOP}"
        x2="{x:.2f}"
        y2="{BOTTOM}"
        stroke="#30363d"
        stroke-width="1"
    />
    '''


# ============================================================
# AREA UNDER LINE
# ============================================================

if points:

    area_points = [
        f"{x:.2f},{y:.2f}"
        for x, y, _, _ in points
    ]

    first_x = points[0][0]
    last_x = points[-1][0]

    # Start at bottom-left
    area_points.insert(
        0,
        f"{first_x:.2f},{BOTTOM}"
    )

    # End at bottom-right of the plotted data
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
# MAIN GREEN LINE
# ============================================================

if points:

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

for x, y, count, contribution_date in points:

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
# X-AXIS DATE LABELS
# ============================================================

for index in label_indices:

    x = x_position(index)

    current_date = dates[index]

    label = (
        f"{current_date.strftime('%b')} "
        f"{current_date.day}"
    )

    svg += f'''
    <text
        x="{x:.2f}"
        y="{BOTTOM + 22}"
        text-anchor="middle"
        fill="#8b949e"
        font-size="11"
        font-family="Arial, Helvetica, sans-serif"
    >
        {escape(label)}
    </text>
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
# GITHUB ACTION LOG
# ============================================================

print("========================================")
print("Contribution graph generated successfully")
print("========================================")

print(f"User: {GITHUB_USERNAME}")
print(f"Month: {month_name} {year}")
print(
    f"Total contributions: "
    f"{total_contributions}"
)
print(
    f"Days plotted: "
    f"{len(dates)}"
)
print(
    f"Maximum daily contributions: "
    f"{max_count}"
)
print(
    f"Y-axis maximum: "
    f"{y_max}"
)
print(
    f"Output: "
    f"{OUTPUT_FILE}"
)
