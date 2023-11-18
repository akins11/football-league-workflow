import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np



def league_standing():

    urls = [
        {"url": "https://www.skysports.com/ligue-1-table", "source": "Ligue 1"},
        {"url": "https://www.skysports.com/premier-league-table", "source": "Premier League"},
        {"url": "https://www.skysports.com/la-liga-table", "source": "la liga"},
        {"url": "https://www.skysports.com/bundesliga-table", "source": "Bundesliga"},
        {"url": "https://www.skysports.com/serie-a-table", "source": "Seria A"},
        {"url": "https://www.skysports.com/eredivisie-table", "source": "Eredivisie"},
        {"url": "https://www.skysports.com/scottish-premier-table", "source": "Scottish premiership"}
    ]
    
    dfs = []

    for url_info in urls:
        url = url_info["url"]
        source = url_info["source"]

        # Send HTTP Request and Parse HTML
        r = requests.get(url)
        soup = BeautifulSoup(r.text, "lxml")

        # Find and Extract Table Headers
        table = soup.find("table", class_="standing-table__table")
        headers = table.find_all("th")
        titles = [i.text for i in headers]

        # Create an Empty DataFrame
        df = pd.DataFrame(columns=titles)

        # Iterate Through Table Rows and Extract Data
        rows = table.find_all("tr")

        for i in rows[1:]:
            data = i.find_all("td")
            row = [tr.text.strip() for tr in data]  # Apply .strip() to remove \n
            l = len(df)
            df.loc[l] = row

        # Add a column for source URL
        df["league_name"] = source                         

        # Append the DataFrame to the list
        dfs.append(df)

    # Concatenate all DataFrames into a single DataFrame
    football_standing = pd.concat(dfs, ignore_index=True)

    # Get the higest match played in order to extract the current match week
    match_week_dict = {}

    for league_name in football_standing["league_name"].unique().tolist(): 
        f_league = (
            football_standing
                .query(f"league_name == '{league_name}'")["Pl"]
                .value_counts()
                .to_frame()
                .reset_index()
                .sort_values(by="count", ascending=False)
        )

        # Get the highest match week value based on the number of teams
        match_week_dict[league_name] = f_league.query(f"count == {f_league['count'].max()}").iloc[0,0]
    
    # assign match week
    football_standing["match_week"] = football_standing["league_name"].map(match_week_dict)

    # columns names 
    df_cols = ["match_week", "#", "Team", "Pl", "W", "D", "L", "F", "A", "GD", "Pts", "Last 6", "league_name"]

    # Select and rearrange columns
    football_standing = football_standing[df_cols]

    # Renames columns
    football_standing = football_standing.rename(columns={
        "#": "position", 
        "Team": "club",
        "Pl": "played", 
        "W": "win", 
        "D": "drawn", 
        "L": "lost",
        "F": "GF", 
        "A": "GA", 
        "Pts": "points"
    })

    football_standing = football_standing.drop("Last 6", axis=1)

    # Previous table
    previous_table = pd.read_csv(
        "data/football_league.csv"
    )

    # Combine current table with previous table and drop duplicate rows
    football_standing = (
        pd.concat([previous_table, football_standing], ignore_index=True)
            .drop_duplicates()
            .sort_values(by=["league_name", "match_week"], ascending=True)
            .drop_duplicates(subset=["match_week", "club"], keep="last")
            .assign(
                club = lambda _: np.where(_['club'] == '1. FC Heidenheim 1846', 'FC Heidenheim 1846', 
                              np.where(_['club'] == '1. FC Union Berlin', 'FC Union Berlin', _['club'])),
            )
            .assign(club = lambda _: _["club"].str.replace("*", "").str.strip())
    )

    football_standing.to_csv(
        "data/football_league.csv", 
        index=False
    )
    



def get_league_scores():

    url = "https://www.skysports.com/football-results"
    r = requests.get(url)
    soup = BeautifulSoup(r.text, "lxml")

    home_team = soup.find_all("span", class_="matches__item-col matches__participant matches__participant--side1")
    x = [name.strip() for i in home_team for name in i.stripped_strings]

    scores = soup.find_all("span", class_="matches__teamscores")
    s = [name.strip().replace('\n\n', '\n') for i in scores for name in i.stripped_strings]
    appended_scores = [f"{s[i]}\n{s[i+1]}".replace('\n', ' ') for i in range(0, len(s), 2)]

    away_team = soup.find_all("span", class_="matches__item-col matches__participant matches__participant--side2")
    y = [name.strip() for i in away_team for name in i.stripped_strings]

    # Make sure all arrays have the same length
    min_length = min(len(x), len(appended_scores), len(y))

    scores = pd.DataFrame({
        "home_team": x[:min_length], 
        "scores": appended_scores[:min_length], 
        "away_team": y[:min_length]
    })

    # Drop all female teams scores
    contain_str = r"Women|Ladies|Femenino|Femminile|Féminines|Vrouwen"
    scores = scores[
        (~scores["home_team"].str.contains(contain_str, case=False)) | 
        (~scores["away_team"].str.contains(contain_str, case=False))
    ]

    # create an identifier column
    scores["type"] = "current"

    # Read in previous week scores
    previous_scores = pd.read_csv(
        "data/football_scores.csv"
    )

    # previous scores clubs
    list_list = [previous_scores[clubs].to_list() for clubs in ["home_team", "away_team"]]
    prev_clubs = [item for sublist in list_list for item in sublist]

    # current scores clubs
    list_list = [scores[clubs].to_list() for clubs in ["home_team", "away_team"]]
    curr_clubs = [item for sublist in list_list for item in sublist]

    # get the list of clubs that are presently not in the current list of clubs
    missing_clubs = [item for item in prev_clubs if item not in curr_clubs]

    if len(missing_clubs) != 0:
        # get all the scores of the missing clubs
        missing_clubs_df = (
            previous_scores
                .query(f"home_team in {missing_clubs} or away_team in {missing_clubs}")
                .reset_index(drop=True)
                .assign(type = "previous")
        )

        # concatinate the missing club scores to the current table
        scores = pd.concat([scores, missing_clubs_df]).drop_duplicates()


    scores.to_csv(
        "data/football_scores.csv",
        index=False
    )






# Run functions
league_standing()

get_league_scores()