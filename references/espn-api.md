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
WARNING: verified 2026-08-26 — this returns a ~100-byte stub containing only
`fullViewLink`, not standings data. Use `{CORE}/seasons/{year}/types/{st}/groups`
or read records off `{SITE}/teams` instead.

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

## Response shapes

Generated 2026-08-26 from live payloads (2025 season, week 1, event `401772510`,
team `12` = Kansas City). These are pinned to completed data, so they stay
reproducible — but nothing refreshes them, so treat them as a snapshot. Depth-limited — `{...N keys}` means the branch was truncated, not that
it is empty. Sample values are real, so they show the *format* of each field, which
is often the surprising part (IDs are strings, colours have no `#`).

**The single most important structural difference between the two hosts:**

| | SITE | CORE |
|---|---|---|
| Returns | fully inline objects | `{count, pageIndex, pageSize, pageCount, items[]}` |
| Nested entities | embedded | `$ref` URLs needing a second GET |
| Cost of "list N players" | 1 request | N+1 requests |

That is why this client prefers SITE wherever both can answer a question, and why
`get_depth_chart` regexes athlete IDs out of `$ref` URLs rather than resolving them.

### `/teams` — team directory

```
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams
```

All 32 teams. The only way to map a name to ESPN's team IDs, which match no other NFL data source.

Data lives at `sports[0].leagues[0].teams[].team`:

```yaml
{
  abbreviation: str ("ARI")
  alternateColor: str ("ffffff")
  color: str ("a40227")
  displayName: str ("Arizona Cardinals")
  id: str ("22")
  isActive: bool (True)
  isAllStar: bool (False)
  links: [  # 6 items
    {...8 keys}
  ]
  location: str ("Arizona")
  logos: [  # 17 items
    {...5 keys}
  ]
  name: str ("Cardinals")
  nickname: str ("Cardinals")
  shortDisplayName: str ("Cardinals")
  slug: str ("arizona-cardinals")
  uid: str ("s:20~l:28~t:22")
}
```

### `/scoreboard` — week's games

```
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard?week=1&dates=2025&seasontype=2
```

Season selector is `dates`, **not** `year`. The event stub holds only id/name/date/status; everything else is in `competitions[0]`.

Data lives at `events[].competitions[0]`:

```yaml
{
  id: str ("401772510")
  uid: str ("s:20~l:28~e:401772510~c:401772510")
  date: str ("2025-09-05T00:20Z")
  attendance: int (69879)
  type: {
    id: str ("1")
    abbreviation: str ("STD")
  }
  timeValid: bool (True)
  neutralSite: bool (False)
  conferenceCompetition: bool (False)
  playByPlayAvailable: bool (True)
  recent: bool (True)
  venue: {
    id: str ("3806")
    fullName: str ("Lincoln Financial Field")
    address: {...3 keys}
    indoor: bool (False)
  }
  competitors: [  # 2 items
    {...12 keys}
  ]
  notes: [] (empty)
  status: {
    clock: float (0.0)
    displayClock: str ("0:00")
    period: int (4)
    type: {...7 keys}
    isTBDFlex: bool (False)
  }
  broadcasts: [  # 1 items
    {...2 keys}
  ]
  leaders: [  # 3 items
    {...5 keys}
  ]
  format: {
    regulation: {...1 keys}
  }
  startDate: str ("2025-09-05T00:20Z")
  broadcast: str ("NBC/Peacock")
  geoBroadcasts: [  # 2 items
    {...5 keys}
  ]
  highlights: [] (empty)
  headlines: [  # 1 items
    {...3 keys}
  ]
}
```

### `/summary` — one game (richest endpoint, ~400 KB)

```
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary?event=401772510
```

Take `event` from the scoreboard. A finished game's summary is immutable, which is why it is the only thing cached to disk.

```yaml
{
  boxscore: {...2 keys}
  format: {...3 keys}
  gameInfo: {...3 keys}
  drives: {...1 keys}
  leaders: [...] (2 items)
  injuries: [...] (2 items)
  broadcasts: [...] (1 items)
  pickcenter: [] (empty)
  odds: [] (empty)
  againstTheSpread: [...] (2 items)
  scoringPlays: [...] (8 items)
  news: {...3 keys}
  winprobability: [...] (164 items)
  article: {...27 keys}
  videos: [] (empty)
  header: {...8 keys}
  wallclockAvailable: bool (True)
  meta: {...8 keys}
  standings: {...4 keys}
}
```

### `/summary` → `drives.previous[]`

Data lives at `drives.previous[]`:

```yaml
{
  id: str ("4017725101")
  description: str ("6 plays, 53 yards, 3:11")
  team: {
    id: str ("6")
    name: str ("Cowboys")
    abbreviation: str ("DAL")
    displayName: str ("Dallas Cowboys")
    shortDisplayName: str ("Cowboys")
    logos: [...] (17 items)
  }
  start: {
    period: {...2 keys}
    clock: {...1 keys}
    yardLine: int (53)
    text: str ("DAL 47")
  }
  end: {
    period: {...2 keys}
    clock: {...1 keys}
    yardLine: int (0)
    text: str ("PHI 0")
  }
  timeElapsed: {
    displayValue: str ("3:11")
  }
  yards: int (53)
  isScore: bool (True)
  offensivePlays: int (6)
  result: str ("TD")
  shortDisplayResult: str ("TD")
  displayResult: str ("Touchdown")
  plays: [  # 9 items
    {...19 keys}   # expanded below
  ]
}
```

### `/summary` → `drives.previous[].plays[]` — play-by-play

The deepest useful level of the summary payload, and what `get_week_big_plays` reads. This game has 16 drives and 169 plays; a full week is ~16x that.

Key presence across all 169 plays — **18 always present, 4 conditional**:

| Key | Present | Appears when |
|---|---|---|
| `yardsAfterCatch` | 42/169 | the play was a completed pass |
| `penalty` | 13/169 | the play drew a flag (`isPenalty` true) |
| `scoringType` | 8/169 | `scoringPlay` is true |
| `pointAfterAttempt` | 5/169 | a touchdown's try is folded into this play |

Shape below is a **synthesised superset** — the base is a rushing touchdown, with each conditional key grafted in from whichever play carries it. No single play has all four.

```yaml
{
  awayScore: int (7)
  clock: {
    displayValue: str ("11:49")
  }
  end: {
    down: int (-1)
    distance: int (10)
    yardLine: int (0)
    yardsToEndzone: int (0)
    team: {
      id: str ("6")
    }
  }
  homeScore: int (0)
  id: str ("401772510247")
  isPenalty: bool (False)
  isTurnover: bool (False)
  modified: str ("2025-09-05T05:06Z")
  period: {
    number: int (1)
  }
  priority: bool (False)
  scoringPlay: bool (True)
  sequenceNumber: str ("24700")
  start: {
    down: int (1)
    distance: int (1)
    yardLine: int (1)
    yardsToEndzone: int (1)
    downDistanceText: str ("1st & Goal at PHI 1")
    shortDownDistanceText: str ("1st & Goal")
    possessionText: str ("PHI 1")
    team: {
      id: str ("6")
    }
  }
  statYardage: int (1)
  teamParticipants: [  # 2 items
    {
      team: {...1 keys}
      id: str ("6")
      order: int (1)
      type: str ("offense")
    }
  ]
  text: str ("J.Williams left guard for 1 yard, TOUC...")
  type: {
    id: str ("68")
    text: str ("Rushing Touchdown")
    abbreviation: str ("TD")
  }
  wallclock: str ("2025-09-05T00:30:57Z")
  yardsAfterCatch: int (0)
  penalty: {
    yards: int (15)
    type: {
      slug: str ("disqualification")
      text: str ("Disqualification")
    }
    status: {
      slug: str ("accepted")
      text: str ("Accepted")
    }
  }
  scoringType: {
    name: str ("touchdown")
    displayName: str ("Touchdown")
    abbreviation: str ("TD")
  }
  pointAfterAttempt: {
    id: int (61)
    text: str ("Extra Point Good")
    abbreviation: str ("Extra Point Good")
    value: int (1)
  }
}
```

**Reading it:**

- `statYardage` is the yardage field, and it is populated for *every* play type including kicks. Sorting on it without filtering by `type.text` gives a board of field goals. Real output from this game:

  ```
   58 yds  Field Goal Good      J.Elliott 58 yard field goal is GOOD, Cent
   53 yds  Field Goal Good      B.Aubrey 53 yard field goal is GOOD, Cente
   51 yds  Pass Reception       (Shotgun) J.Hurts pass deep middle to J.Do
   49 yds  Rush                 (Shotgun) M.Sanders left end to PHI 11 for
   41 yds  Field Goal Good      B.Aubrey 41 yard field goal is GOOD, Cente
   34 yds  Penalty              (Shotgun) D.Prescott pass incomplete deep 
  ```

  Two of the top three are field goals and a penalty is sixth — which is why `get_week_big_plays` restricts to `SCRIMMAGE_PLAY_TYPES` (`Rush`, `Rushing Touchdown`, `Pass Reception`, `Passing Touchdown`).

- `start.down` / `end.down` are `-1` at a drive boundary rather than null.
- `teamParticipants[].type` is `offense` / `defense`, and `.id` is the team ID — use it rather than the drive's team when the ball changed hands.
- `text` is the official play-by-play string; `type.text` is the machine-readable classifier and the thing worth branching on.
- `type.text` values in this game: `Rush` (54), `Pass Reception` (40), `Pass Incompletion` (17), `Official Timeout` (12), `Kickoff` (9), `Timeout` (9), `Penalty` (7), `Rushing Touchdown` (5), …

### `/summary` → `scoringPlays[]`

Data lives at `scoringPlays[]`:

```yaml
{
  id: str ("401772510247")
  type: {
    id: str ("68")
    text: str ("Rushing Touchdown")
    abbreviation: str ("TD")
  }
  text: str ("Javonte Williams 1 Yd Rush (Brandon Au...")
  awayScore: int (7)
  homeScore: int (0)
  period: {
    number: int (1)
  }
  clock: {
    value: float (709.0)
    displayValue: str ("11:49")
  }
  team: {
    id: str ("6")
    uid: str ("s:20~l:28~t:6")
    displayName: str ("Dallas Cowboys")
    abbreviation: str ("DAL")
    links: [...] (2 items)
    logo: str ("https://a.espncdn.com/i/teamlogos/nfl/...")
    logos: [...] (4 items)
  }
  scoringType: {
    name: str ("touchdown")
    displayName: str ("Touchdown")
    abbreviation: str ("TD")
  }
}
```

### `/teams/{id}?enable=roster` — roster with inline injuries

```
GET https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/12?enable=roster,projection,stats
```

`?enable=roster` is load-bearing — without it you get the team stub and no players. Each athlete carries `injuries[]` inline, so no per-player follow-up request is needed.

Data lives at `team.athletes[]`:

```yaml
{
  id: str ("4885466")
  uid: str ("s:20~l:28~a:4885466")
  guid: str ("3b79a0b5-667a-34ac-8a5c-d67b45363beb")
  type: str ("football")
  alternateIds: {
    sdr: str ("4885466")
  }
  firstName: str ("Jeff")
  lastName: str ("Caldwell")
  fullName: str ("Jeff Caldwell")
  displayName: str ("Jeff Caldwell")
  shortName: str ("J. Caldwell")
  weight: float (215.0)
  displayWeight: str ("215 lbs")
  height: float (77.0)
  displayHeight: str ("6' 5"")
  age: int (23)
  dateOfBirth: str ("2003-03-02T08:00Z")
  links: [  # 12 items
    {...7 keys}
  ]
  birthPlace: {
    city: str ("Louisville")
    state: str ("KY")
    country: str ("USA")
  }
  college: {
  }
  slug: str ("jeff-caldwell")
  headshot: {
    href: str ("https://a.espncdn.com/i/headshots/nfl/...")
    alt: str ("Jeff Caldwell")
  }
  jersey: str ("8")
  position: {
    id: str ("1")
    name: str ("Wide Receiver")
    displayName: str ("Wide Receiver")
    abbreviation: str ("WR")
    leaf: bool (True)
    parent: {...0 keys}
  }
  injuries: [  # 1 items
    {...9 keys}
  ]
  ... 7 more keys
}
```

### `/depthcharts` — CORE host

```
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/teams/12/depthcharts
```

Different host from everything above. Players are `$ref` URLs rather than inline objects — resolve them with a second GET, or regex the ID out of the URL as this client does. `season` is required by the path but does **not** select a historical chart: every year returns today's chart.

Data lives at `items[].positions.{slot}.athletes[]`:

```yaml
{
  id: str ("16")
  name: str ("Base 4-3 D")
  positions: {
    lde: {
      position: {
        $ref: str ("http://sports.core.api.espn.com/v2/spo...")
        id: str ("11")
        name: str ("Left Defensive End")
        displayName: str ("Left Defensive End")
        abbreviation: str ("LDE")
        leaf: bool (True)
        parent: {
          $ref: str ("http://sports.core.api.espn.com/v2/spo...")
        }
      }
      athletes: [  # 6 items
        {
          slot: int (1)
          athlete: {...1 keys}
          rank: int (1)
        }
      ]
    }
    ...: str ("one entry per position slot")
  }
}
```

`items[]` are formation groups — this team has 3: `Base 4-3 D`, `Special Teams`, `3WR 1TE`.

### `/leaders` — season stat leaders (CORE)

```
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/2025/types/2/leaders
```

Not used by this client. Season-to-date, so it does not answer week-specific questions.

Data lives at `categories[].leaders[]`:

```yaml
{
  name: str ("passingYards")
  displayName: str ("Passing Yards")
  shortDisplayName: str ("PYDS")
  abbreviation: str ("YDS")
  leaders: [  # 1 items
    {
      displayValue: str ("4707")
      value: float (4707.0)
      rel: [...] (1 items)
      athlete: {...1 keys}
      team: {...1 keys}
      statistics: {...1 keys}
    }
  ]
}
```

### CORE pagination envelope

```
GET https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/athletes?limit=1000&active=true&position=WR
```

Shared by every CORE collection (`/athletes`, `/events`, `/teams/{id}/athletes`). `items[]` are `$ref` URLs, so listing N players costs N+1 requests.

```yaml
{
  count: int (7453)
  pageIndex: int (1)
  pageSize: int (5)
  pageCount: int (1491)
  items: [  # 5 items
    {...1 keys}
  ]
}
```

---

## Notes

- The ESPN API is unofficial and undocumented — endpoints may change without notice
- `$ref` links in responses must be followed with a second GET to get full data
- Rate limit: not published; cache responses and avoid hammering in tight loops
- Historical data is generally available back to ~2002
