# API Endpoints Documentation

## ESPNcricinfo API (`hs-consumer-api.espncricinfo.com`)

All endpoints are JSON. No API key required (public consumer API).

### Series Schedule
```
GET /v1/pages/series/schedule?seriesId={series_id}
```
Returns list of matches in a series with dates, teams, venues, and status.

### Match Details
```
GET /v1/pages/match/details?seriesId={series_id}&matchId={match_id}
```
Returns match summary, playing XI, toss result, and match status.

### Match Scorecard
```
GET /v1/pages/match/scorecard?seriesId={series_id}&matchId={match_id}
```
Returns full scorecard with batting/bowling details per innings.

### Ball-by-Ball Commentary
```
GET /v1/pages/match/comments?seriesId={series_id}&matchId={match_id}&inningNumber={1|2}&page={page}
```
Returns paginated ball-by-ball commentary with delivery-level data.

### Player Stats
```
GET /v1/pages/player/stats?playerId={player_id}
```
Returns career and format-wise statistics.

### Player Profile
```
GET /v1/pages/player/summary?playerId={player_id}
```
Returns player bio, image, and recent performances.

### Series Squads
```
GET /v1/pages/series/squads?seriesId={series_id}
GET /v1/pages/series/squads?seriesId={series_id}&teamId={team_id}
```
Returns full squad lists for all teams or a specific team.

### Venue Details
```
GET /v1/pages/ground/details?groundId={ground_id}
```
Returns venue information including city, country, and match history.

---

## Cricbuzz

Cricbuzz uses HTML pages with embedded data. Some AJAX endpoints exist.

### Match Scorecard (AJAX)
```
GET /api/html/cricket-scorecard/{match_id}
```
Returns HTML fragment of the scorecard.

### Match Commentary (AJAX)
```
GET /api/html/cricket-commentary/{match_id}
```
Returns HTML fragment of ball-by-ball commentary.

### Series Matches
```
GET /cricket-series/{series_slug}/matches
```
HTML page listing all matches in a series.

---

## IPLT20 Official

The official IPL website is heavily JavaScript-rendered. Most data requires
browser automation (Playwright) to scrape.

### Match Results
```
GET /matches/results/{season}
```
HTML page with match result cards.

### Team Squad
```
GET /teams/{team_slug}/squad
```
HTML page with player cards.

### Season Stats
```
GET /stats/{season}/most-runs
GET /stats/{season}/most-wickets
```
HTML tables with season batting/bowling leaderboards.

### Venues
```
GET /venues
GET /venues/{venue_slug}
```
HTML pages with venue information.

---

## Weather APIs

### OpenWeatherMap
```
GET https://api.openweathermap.org/data/2.5/weather?q={city}&appid={key}&units=metric
GET https://api.openweathermap.org/data/2.5/onecall/timemachine?lat={lat}&lon={lon}&dt={unix_ts}&appid={key}&units=metric
```
Requires free API key from [openweathermap.org](https://openweathermap.org/api).

### VisualCrossing
```
GET https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{city}/{date}?unitGroup=metric&key={key}
```
Requires free API key from [visualcrossing.com](https://www.visualcrossing.com/weather-api).

---

## IPL Series IDs (ESPNcricinfo)

| Season | Series ID |
|--------|-----------|
| 2008   | 313494    |
| 2009   | 374163    |
| 2010   | 418064    |
| 2011   | 466304    |
| 2012   | 520932    |
| 2013   | 586733    |
| 2014   | 695871    |
| 2015   | 791129    |
| 2016   | 968923    |
| 2017   | 1078425   |
| 2018   | 1131611   |
| 2019   | 1165643   |
| 2020   | 1210595   |
| 2021   | 1249214   |
| 2022   | 1298423   |
| 2023   | 1345038   |
| 2024   | 1410320   |
| 2025   | 1449924   |
