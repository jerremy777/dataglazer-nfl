# ESPN API Reference

Quick reference for common NFL data fetches. All endpoints require no API key.

Base URLs:
- `CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"`
- `SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"`
- `WEB  = "https://site.web.api.espn.com/apis/site/v3/sports/football/nfl"`

Season types: `1` = preseason, `2` = regular season, `3` = postseason

---

## Common Endpoints

### Season stat leaders (receiving, passing, rushing)
```
GET {CORE}/seasons/{year}/types/{season_type}/leaders
```
Returns top players per stat category. Each entry has athlete `$ref` + value.

### Active athletes by position
```
GET {CORE}/athletes?limit=1000&active=true&position=WR
GET {CORE}/athletes?limit=1000&active=true&position=QB
GET {CORE}/athletes?limit=1000&active=true&position=RB
```

### Team list (with IDs)
```
GET {SITE}/teams
```

### Team roster for a season
```
GET {CORE}/seasons/{year}/teams/{team_id}/athletes?limit=200
```

### Scoreboard (current week)
```
GET {SITE}/scoreboard
```

### Scoreboard (specific date)
```
GET {SITE}/scoreboard?dates=20241215
```

### Standings
```
GET {SITE}/standings
```

### Schedule for a team
```
GET {CORE}/seasons/{year}/teams/{team_id}/events
```

---

## Fetch helper

```python
import httpx

CORE = "https://sports.core.api.espn.com/v2/sports/football/leagues/nfl"
SITE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


def get(url, **params):
    r = httpx.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()


def resolve_ref(ref_url):
    """Follow a $ref link."""
    return get(ref_url)


def get_leaders(year=2024, season_type=2):
    return get(f"{CORE}/seasons/{year}/types/{season_type}/leaders")


def get_teams():
    return get(f"{SITE}/teams")
```

---

## Extracting receiving yard leaders

```python
def get_receiving_leaders(year=2024, limit=20):
    data = get_leaders(year)

    # Find the receivingYards category
    categories = data.get("categories", [])
    recv_cat = next((c for c in categories if c.get("name") == "receivingYards"), None)

    if not recv_cat:
        return []

    results = []
    for entry in recv_cat.get("leaders", [])[:limit]:
        athlete_data = resolve_ref(entry["athlete"]["$ref"])
        results.append(
            {
                "name": athlete_data.get("displayName", "Unknown"),
                "team": athlete_data.get("team", {}).get("abbreviation", ""),
                "yards": entry["value"],
            }
        )

    return results
```

---

## Notes

- The ESPN API is unofficial and undocumented — endpoints may change without notice
- `$ref` links in responses must be followed with a second GET to get full data
- Rate limit: not published; cache responses and avoid hammering in tight loops
- Historical data is generally available back to ~2002
