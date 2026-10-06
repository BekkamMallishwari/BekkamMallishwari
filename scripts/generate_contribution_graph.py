import os
import html
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


# ============================================================
# CONFIGURATION
# ============================================================

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USERNAME = os.environ.get(
    "GITHUB_USERNAME",
    "BekkamMallishwari"
)

OUTPUT_FILE = "github-metrics.svg"


# ============================================================
# CURRENT MONTH - INDIA TIME
# ============================================================

INDIA_TZ = ZoneInfo("Asia/Kolkata")

today = datetime.now(INDIA_TZ).date()

# First day of current month
start_date = today.replace(day=1)

# First day of next month
if start_date.month == 12:
    next_month = start_date.replace(
        year=start_date.year + 1,
        month=1,
        day=1
    )
else:
    next_month = start_date.replace(
        month=start_date.month + 1,
        day=1
    )

# Last day of current month
end_date = next_month - timedelta(days=1)


print("========================================")
print("Contribution Graph")
print("========================================")
print(f"Username:   {GITHUB_USERNAME}")
print(f"Start date: {start_date}")
print(f"End date:   {end_date}")
print("Timezone:   Asia/Kolkata")
print("========================================")


# ============================================================
# CHECK TOKEN
# ============================================================

if not GITHUB_TOKEN:
    raise RuntimeError("GITHUB_TOKEN is not set")


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
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            weekday
          }
        }
      }
    }
  }
}
"""


# ============================================================
# GITHUB API DATE RANGE
# ============================================================

from_datetime = (
    f"{start_date}T00:00:00+05:30"
)

to_datetime = (
    f"{end_date}T23:59:59+05:30"
)


# ============================================================
# CALL GITHUB API
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

data = response.json()


# ============================================================
# CHECK API ERRORS
# ============================================================

if "errors" in data:
    print("GitHub API errors:")

    for error in data["errors"]:
        print(error)

    raise RuntimeError(
        "GitHub GraphQL API returned errors"
    )


# ============================================================
# GET USER DATA
# ============================================================

user_data = (
    data
    .get("data", {})
    .get("user")
)

if not user_data:
    raise RuntimeError(
        f"GitHub user '{GITHUB_USERNAME}' was not found"
    )


# ============================================================
# GET CONTRIBUTION CALENDAR
# ============================================================

calendar = (
    user_data[
        "contributionsCollection"
    ][
        "contributionCalendar"
    ]
)

total_contributions = (
    calendar["totalContributions"]
)


# ============================================================
# GET CONTRIBUTION DAYS
# ============================================================

days = []

for week in calendar["weeks"]:
    for day in week["contributionDays"]:
        days.append(day)

days.sort(
    key=lambda x: x["date"]
)


# ============================================================
# DATE -> CONTRIBUTION COUNT
# ============================================================

day_map = {
    day["date"]: day["contributionCount"]
    for day in days
}


# ============================================================
# MAX CONTRIBUTION
# ============================================================

max_count = max(
    (
        day["contributionCount"]
        for day in days
    ),
    default=0
)


# ============================================================
# COLORS
# ============================================================

LEVEL_0 = "#ebedf0"
LEVEL_1 = "#9be9a8"
LEVEL_2 = "#40c463"
LEVEL_3 = "#30a14e"
LEVEL_4 = "#216e39"


def get_color(count):

    if count == 0:
        return LEVEL_0

    if max_count <= 1:
        return LEVEL_1

    ratio = count / max_count

    if ratio <= 0.25:
        return LEVEL_1

    if ratio <= 0.50:
        return LEVEL_2

    if ratio <= 0.75:
        return LEVEL_3

    return LEVEL_4


# ============================================================
# GRAPH SIZE
# ============================================================

CELL_SIZE = 16
CELL_GAP = 4
CELL_STEP = CELL_SIZE + CELL_GAP

LEFT_MARGIN = 45
TOP_MARGIN = 55
RIGHT_MARGIN = 25
BOTTOM_MARGIN = 35


# ============================================================
# CREATE CURRENT MONTH DAYS
# ============================================================

current = start_date

month_days = []

while current <= end_date:

    month_days.append(current)

    current += timedelta(days=1)


# ============================================================
# CALENDAR POSITION
# ============================================================

# Python:
# Monday = 0
# Sunday = 6
#
# Convert to:
# Sunday = 0
# Monday = 1
# ...
# Saturday = 6

first_weekday = (
    start_date.weekday() + 1
) % 7


number_of_days = len(month_days)

number_of_cells = (
    first_weekday + number_of_days
)

columns = 7

rows = (
    number_of_cells + columns - 1
) // columns


# ============================================================
# SVG SIZE
# ============================================================

width = (
    LEFT_MARGIN
    + columns * CELL_STEP
    + RIGHT_MARGIN
)

height = (
    TOP_MARGIN
    + rows * CELL_STEP
    + BOTTOM_MARGIN
)


# ============================================================
# MONTH NAME
# ============================================================

month_name = start_date.strftime(
    "%B %Y"
)


# ============================================================
# START SVG
# ============================================================

svg = []

svg.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{width}" '
    f'height="{height}" '
    f'viewBox="0 0 {width} {height}">'
)


# ============================================================
# BACKGROUND
# ============================================================

svg.append(
    '<rect '
    'width="100%" '
    'height="100%" '
    'fill="white" '
    'rx="8"/>'
)


# ============================================================
# TITLE
# ============================================================

safe_username = html.escape(
    GITHUB_USERNAME
)

svg.append(
    f'<text '
    f'x="{LEFT_MARGIN}" '
    f'y="24" '
    f'font-family="Arial, sans-serif" '
    f'font-size="16" '
    f'font-weight="bold" '
    f'fill="#24292f">'
    f'{safe_username}\'s Contribution Graph'
    f'</text>'
)


# ============================================================
# TOTAL CONTRIBUTIONS
# ============================================================

svg.append(
    f'<text '
    f'x="{LEFT_MARGIN}" '
    f'y="43" '
    f'font-family="Arial, sans-serif" '
    f'font-size="11" '
    f'fill="#57606a">'
    f'{total_contributions} contributions in '
    f'{html.escape(month_name)}'
    f'</text>'
)


# ============================================================
# WEEKDAY LABELS
# ============================================================

weekday_labels = [
    "Sun",
    "Mon",
    "Tue",
    "Wed",
    "Thu",
    "Fri",
    "Sat",
]

for column, label in enumerate(
    weekday_labels
):

    x = (
        LEFT_MARGIN
        + column * CELL_STEP
        + CELL_SIZE / 2
    )

    svg.append(
        f'<text '
        f'x="{x}" '
        f'y="{TOP_MARGIN - 12}" '
        f'text-anchor="middle" '
        f'font-family="Arial, sans-serif" '
        f'font-size="8" '
        f'fill="#57606a">'
        f'{label}'
        f'</text>'
    )


# ============================================================
# DRAW CONTRIBUTION CELLS
# ============================================================

for index, current_date in enumerate(
    month_days
):

    date_string = (
        current_date.strftime(
            "%Y-%m-%d"
        )
    )

    count = day_map.get(
        date_string,
        0
    )

    position = (
        first_weekday + index
    )

    row = position // columns
    column = position % columns

    x = (
        LEFT_MARGIN
        + column * CELL_STEP
    )

    y = (
        TOP_MARGIN
        + row * CELL_STEP
    )

    color = get_color(count)

    if count == 1:
        contribution_text = "contribution"
    else:
        contribution_text = "contributions"

    tooltip = (
        f"{count} {contribution_text} "
        f"on {date_string}"
    )

    svg.append(
        f'<rect '
        f'x="{x}" '
        f'y="{y}" '
        f'width="{CELL_SIZE}" '
        f'height="{CELL_SIZE}" '
        f'rx="3" '
        f'ry="3" '
        f'fill="{color}">'
        f'<title>'
        f'{html.escape(tooltip)}'
        f'</title>'
        f'</rect>'
    )


# ============================================================
# LEGEND
# ============================================================

legend_y = height - 18

svg.append(
    f'<text '
    f'x="{LEFT_MARGIN}" '
    f'y="{legend_y}" '
    f'font-family="Arial, sans-serif" '
    f'font-size="8" '
    f'fill="#57606a">'
    f'Less'
    f'</text>'
)


legend_colors = [
    LEVEL_0,
    LEVEL_1,
    LEVEL_2,
    LEVEL_3,
    LEVEL_4,
]

legend_start_x = (
    LEFT_MARGIN + 30
)

for index, color in enumerate(
    legend_colors
):

    x = (
        legend_start_x
        + index * 20
    )

    svg.append(
        f'<rect '
        f'x="{x}" '
        f'y="{legend_y - 9}" '
        f'width="12" '
        f'height="12" '
        f'rx="2" '
        f'ry="2" '
        f'fill="{color}"/>'
    )


svg.append(
    f'<text '
    f'x="{legend_start_x + 5 * 20 + 3}" '
    f'y="{legend_y}" '
    f'font-family="Arial, sans-serif" '
    f'font-size="8" '
    f'fill="#57606a">'
    f'More'
    f'</text>'
)


# ============================================================
# CLOSE SVG
# ============================================================

svg.append("</svg>")


# ============================================================
# SAVE GRAPH
# ============================================================

with open(
    OUTPUT_FILE,
    "w",
    encoding="utf-8"
) as file:

    file.write(
        "\n".join(svg)
    )


# ============================================================
# SUCCESS MESSAGE
# ============================================================

print("========================================")
print("Contribution graph generated successfully")
print("========================================")
print(f"Month:         {month_name}")
print(f"Start date:    {start_date}")
print(f"End date:      {end_date}")
print(f"Contributions: {total_contributions}")
print(f"Output file:   {OUTPUT_FILE}")
print("========================================")
