import os
import requests
from datetime import datetime, timezone

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ["GITHUB_USERNAME"]

QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        contributionDays {
          date
          contributionCount
        }
      }
    }
  }
}
"""

now = datetime.now(timezone.utc)

year = now.year
month = now.month

if month == 12:
    next_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
else:
    next_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)

start = datetime(year, month, 1, tzinfo=timezone.utc)

variables = {
    "login": USERNAME,
    "from": start.isoformat(),
    "to": next_month.isoformat(),
}

response = requests.post(
    "https://api.github.com/graphql",
    json={
        "query": QUERY,
        "variables": variables,
    },
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    },
)

response.raise_for_status()

result = response.json()

if "errors" in result:
    raise RuntimeError(result["errors"])

days = result["data"]["user"]["contributionsCollection"][
    "contributionCalendar"
]["contributionDays"]

# Keep only the current month
days = [
    day
    for day in days
    if datetime.fromisoformat(day["date"]).month == month
    and datetime.fromisoformat(day["date"]).year == year
]

days.sort(key=lambda x: x["date"])

counts = [day["contributionCount"] for day in days]

if not counts:
    raise RuntimeError("No contribution data found.")

max_count = max(counts)

# Give the graph some breathing room
y_max = max(7, max_count)

WIDTH = 1100
HEIGHT = 450

LEFT = 80
RIGHT = 40
TOP = 75
BOTTOM = 365

GRAPH_WIDTH = WIDTH - LEFT - RIGHT
GRAPH_HEIGHT = BOTTOM - TOP

count = len(days)

if count == 1:
    x_positions = [LEFT]
else:
    x_positions = [
        LEFT + (GRAPH_WIDTH * i / (count - 1))
        for i in range(count)
    ]


def y_position(value):
    return BOTTOM - (value / y_max) * GRAPH_HEIGHT


points = [
    (x_positions[i], y_position(counts[i]))
    for i in range(count)
]

polyline_points = " ".join(
    f"{x:.2f},{y:.2f}" for x, y in points
)

area_points = (
    f"{LEFT},{BOTTOM} "
    + polyline_points
    + f" {x_positions[-1]:.2f},{BOTTOM}"
)

# Y-axis labels
y_labels = []

for i in range(8):
    value = round(y_max * i / 7)
    y = BOTTOM - (GRAPH_HEIGHT * i / 7)

    y_labels.append(
        f"""
        <text x="68"
              y="{y + 4:.0f}"
              fill="#8b949e"
              font-family="Arial, sans-serif"
              font-size="12"
              text-anchor="end">
            {value}
        </text>
        """
    )

# Horizontal grid
horizontal_lines = []

for i in range(8):
    y = BOTTOM - (GRAPH_HEIGHT * i / 7)

    horizontal_lines.append(
        f'<line x1="{LEFT}" y1="{y:.0f}" '
        f'x2="{WIDTH - RIGHT}" y2="{y:.0f}"/>'
    )

# Vertical grid
vertical_lines = []

for x in x_positions:
    vertical_lines.append(
        f'<line x1="{x:.2f}" y1="{TOP}" '
        f'x2="{x:.2f}" y2="{BOTTOM}"/>'
    )

# Daily date labels
date_labels = []

for i, day in enumerate(days):
    date_obj = datetime.fromisoformat(day["date"])

    # Show every date
    label = date_obj.strftime("%b %-d")

    date_labels.append(
        f"""
        <text x="{x_positions[i]:.2f}"
              y="395"
              fill="#8b949e"
              font-family="Arial, sans-serif"
              font-size="10"
              text-anchor="middle">
            {label}
        </text>
        """
    )

# Contribution points
circles = []

for i, (x, y) in enumerate(points):
    circles.append(
        f"""
        <circle cx="{x:.2f}"
                cy="{y:.2f}"
                r="5"
                fill="#39d353"
                stroke="#0d1117"
                stroke-width="3"/>
        """
    )

month_name = start.strftime("%B %Y")

svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
     width="{WIDTH}"
     height="{HEIGHT}"
     viewBox="0 0 {WIDTH} {HEIGHT}">

  <rect width="{WIDTH}"
        height="{HEIGHT}"
        rx="12"
        fill="#0d1117"/>

  <text x="{WIDTH / 2}"
        y="38"
        text-anchor="middle"
        fill="#58a6ff"
        font-family="Arial, sans-serif"
        font-size="20"
        font-weight="bold">
    Mallishwari's Contribution Graph — {month_name}
  </text>

  <rect x="{LEFT}"
        y="{TOP}"
        width="{GRAPH_WIDTH}"
        height="{GRAPH_HEIGHT}"
        fill="#0d1117"
        stroke="#30363d"
        stroke-width="1"/>

  <g stroke="#30363d" stroke-width="1">
    {"".join(horizontal_lines)}
  </g>

  <g stroke="#21262d" stroke-width="1">
    {"".join(vertical_lines)}
  </g>

  <text x="25"
        y="225"
        transform="rotate(-90 25 225)"
        text-anchor="middle"
        fill="#8b949e"
        font-family="Arial, sans-serif"
        font-size="13">
    Contributions
  </text>

  {"".join(y_labels)}

  <polygon
      points="{area_points}"
      fill="#39d353"
      opacity="0.12"/>

  <polyline
      points="{polyline_points}"
      fill="none"
      stroke="#39d353"
      stroke-width="4"
      stroke-linecap="round"
      stroke-linejoin="round"/>

  <g>
    {"".join(circles)}
  </g>

  <g>
    {"".join(date_labels)}
  </g>

  <text x="{WIDTH / 2}"
        y="425"
        text-anchor="middle"
        fill="#8b949e"
        font-family="Arial, sans-serif"
        font-size="13">
    Date
  </text>

</svg>
"""

with open("github-metrics.svg", "w", encoding="utf-8") as file:
    file.write(svg)

print(f"Generated contribution graph for {month_name}")
print(f"Days: {len(days)}")
print(f"Contributions: {sum(counts)}")
