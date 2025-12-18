import pandas as pd
from demoparser2 import DemoParser
import os
from glob import glob

# Define the path to the 'demos' folder
DEMOS_FOLDER = os.path.join(os.path.dirname(''), "..", "demos")

ASSETS_FOLDER = os.path.join(os.path.dirname(''), "..", "assets")
MAPS_BACKGROUND_FOLDER = os.path.join(ASSETS_FOLDER, "maps_background")

# Load all demos paths
demos_paths = glob(os.path.join(DEMOS_FOLDER, "**", "*.dem"), recursive=True)

# Load all map background images paths
maps_background_paths = {f.split('.')[0]: os.path.join(MAPS_BACKGROUND_FOLDER, f) for f in os.listdir(MAPS_BACKGROUND_FOLDER) if f.endswith('.png')}

def build_round_summary(ticks_df: pd.DataFrame, round_results: pd.DataFrame) -> pd.DataFrame:
    """
    Build a lightweight per-round summary DataFrame from tick-level data.

    Args:
        ticks_df (pd.DataFrame): DataFrame containing tick-level data.
        round_results (pd.DataFrame): DataFrame containing round outcomes.

    Returns:
        pd.DataFrame: Summary DataFrame with players and weapons by team for each round.
    """
    # Build a lightweight per-round summary: players and weapons by team
    def unique_list(series, exclude=(None, 'None', '')):
        if series is None:
            return []
        s = series.dropna()
        vals = [v for v in s.tolist() if v not in exclude]
        # preserve order of first appearance
        return list(dict.fromkeys(vals))

    team_ct_label, team_t_label = 'CT', 'TERRORIST'
    player_col = 'steamid' if 'steamid' in ticks_df.columns else ('name' if 'name' in ticks_df.columns else None)

    # Helper: first non-null value
    def first_non_null(series):
        s = series.dropna()
        return s.iloc[0] if not s.empty else None

    # Determine the first post-freeze tick per round (fallback to time >1s, else earliest)
    import pandas as pd
    rounds_df = pd.DataFrame({'total_rounds_played': sorted(ticks_df['total_rounds_played'].unique())})

    min_tick = (
        ticks_df.groupby('total_rounds_played', as_index=False)['tick']
        .min()
        .rename(columns={'tick': 'min_tick'})
    )
    rounds_df = rounds_df.merge(min_tick, on='total_rounds_played', how='left')

    if 'is_freeze_period' in ticks_df.columns:
        live_tick = (
            ticks_df.loc[ticks_df['is_freeze_period'] == False, ['total_rounds_played', 'tick']]
                .groupby('total_rounds_played', as_index=False)['tick']
                .min()
                .rename(columns={'tick': 'live_tick'})
        )
    else:
        live_tick = pd.DataFrame(columns=['total_rounds_played', 'live_tick'])
    rounds_df = rounds_df.merge(live_tick, on='total_rounds_played', how='left')

    if 'seconds_elapsed_in_round' in ticks_df.columns:
        spawn_tick = (
            ticks_df.loc[ticks_df['seconds_elapsed_in_round'] > 1, ['total_rounds_played', 'tick']]
                .groupby('total_rounds_played', as_index=False)['tick']
                .min()
                .rename(columns={'tick': 'spawn_tick'})
        )
    else:
        spawn_tick = pd.DataFrame(columns=['total_rounds_played', 'spawn_tick'])
    rounds_df = rounds_df.merge(spawn_tick, on='total_rounds_played', how='left')

    rounds_df['first_tick'] = rounds_df['live_tick'].fillna(rounds_df['spawn_tick']).fillna(rounds_df['min_tick'])

    # Keep only rows at the first post-freeze tick per round
    first_ticks = ticks_df.merge(rounds_df[['total_rounds_played', 'first_tick']], on='total_rounds_played', how='left')
    first_ticks = first_ticks[first_ticks['tick'] == first_ticks['first_tick']].copy()

    # Build safe maps for round outcomes to avoid IndexError when missing
    winners_map = {}
    reasons_map = {}
    if 'round_index' in round_results.columns:
        winners_map = round_results.set_index('round_index')['round_winner'].to_dict()
        reasons_map = round_results.set_index('round_index')['round_reason'].to_dict()

    rows = []
    for r, grp in first_ticks.groupby('total_rounds_played'):
        ct = grp[grp['team_name'] == team_ct_label]
        tt = grp[grp['team_name'] == team_t_label]

        ct_players = unique_list(ct[player_col]) if player_col else []
        tt_players = unique_list(tt[player_col]) if player_col else []

        # Team equip values at the first post-freeze tick, using current_equip_value
        if 'current_equip_value' in ct.columns:
            ct_equip = int(ct['current_equip_value'].dropna().sum())
        else:
            ct_equip = None
        if 'current_equip_value' in tt.columns:
            tt_equip = int(tt['current_equip_value'].dropna().sum())
        else:
            tt_equip = None

        rows.append({
            'total_rounds_played': int(r),
            'round_winner': int(winners_map.get(int(r), 0)),
            'round_reason': int(reasons_map.get(int(r), 0)),
            'team_ct_name': team_ct_label,
            'team_t_name': team_t_label,
            'team_ct_players': ct_players,
            'team_t_players': tt_players,
            'team_ct_current_equip_value': ct_equip,
            'team_t_current_equip_value': tt_equip,
        })

    round_summary_df = pd.DataFrame(rows).sort_values('total_rounds_played').reset_index(drop=True)

    round_summary_df['round'] = round_summary_df['total_rounds_played'] + 1
    round_summary_df.drop(columns=['total_rounds_played'], inplace=True)
    return round_summary_df

def set_categorical_data_types(ticks_df: pd.DataFrame) -> pd.DataFrame:
    # Set categorical data types
    ticks_df['weapon_name'] = ticks_df['weapon_name'].astype('category')
    ticks_df['team_name'] = ticks_df['team_name'].astype('category')
    return ticks_df

def filter_initial_round_ticks(ticks_df: pd.DataFrame) -> pd.DataFrame:
    # Ignore initial ticks before the round's freeze time begins (keep freeze/buy + live phase)
    # 1) Find the first tick in each round where freeze is flagged (if available)
    if 'is_freeze_period' in ticks_df.columns:
        freeze_start = (
            ticks_df.loc[ticks_df['is_freeze_period'] == True, ['total_rounds_played', 'tick']]
                .groupby('total_rounds_played', as_index=False)['tick']
                .min()
                .rename(columns={'tick': 'freeze_start_tick'})
        )
    else:
        import pandas as pd
        freeze_start = pd.DataFrame(columns=['total_rounds_played','freeze_start_tick'])

    # 2) Fallback: earliest tick where seconds_elapsed_in_round > 1
    if 'seconds_elapsed_in_round' in ticks_df.columns:
        spawn_defined = (
            ticks_df.loc[ticks_df['seconds_elapsed_in_round'] > 1, ['total_rounds_played', 'tick']]
                .groupby('total_rounds_played', as_index=False)['tick']
                .min()
                .rename(columns={'tick': 'spawn_defined_tick'})
        )
    else:
        import pandas as pd
        spawn_defined = pd.DataFrame(columns=['total_rounds_played','spawn_defined_tick'])

    # 3) Build per-round cutoff tick: prefer freeze_start_tick, else spawn_defined_tick
    cutoffs = freeze_start.merge(spawn_defined, on='total_rounds_played', how='outer')
    cutoffs['keep_from_tick'] = cutoffs['freeze_start_tick'].fillna(cutoffs['spawn_defined_tick'])

    # 4) Join and filter ticks_df to only keep ticks at/after cutoff
    ticks_df = ticks_df.merge(cutoffs[['total_rounds_played', 'keep_from_tick']], on='total_rounds_played', how='left')
    # If a round still lacks a cutoff, default to that round's first tick
    ticks_df['keep_from_tick'] = ticks_df['keep_from_tick'].fillna(ticks_df.groupby('total_rounds_played')['tick'].transform('min'))
    ticks_df = ticks_df[ticks_df['tick'] >= ticks_df['keep_from_tick']].copy()
    ticks_df.drop(columns=['keep_from_tick'], inplace=True)
    return ticks_df

def finalize_ticks_dataframe(ticks_df: pd.DataFrame) -> pd.DataFrame:
    # Seconds elapsed in round
    ticks_df['seconds_elapsed_in_round'] = (ticks_df['game_time'] - ticks_df['round_start_time']).clip(lower=0)
    ticks_df.drop(columns=['round_start_time', 'game_time'], inplace=True)
    return ticks_df

def integrate_round_results(ticks_df: pd.DataFrame, round_results: pd.DataFrame) -> pd.DataFrame:
    # Join with round-level outcomes computed before filtering
    ticks_df = ticks_df.merge(round_results, left_on='total_rounds_played', right_on='round_index', how='left')

    # Drop non-official rounds (e.g., warmup)
    ticks_df = ticks_df.dropna(subset=['round_winner']).copy()
    ticks_df['round_winner'] = ticks_df['round_winner'].astype('int32')
    ticks_df['round_reason'] = ticks_df['round_reason'].fillna(0).astype('int32')

    # Replace per-tick status/reason with aggregated round results
    ticks_df['round_win_status'] = ticks_df['round_winner']
    ticks_df['round_win_reason'] = ticks_df['round_reason']

    # Clean helper columns
    ticks_df.drop(columns=['round_winner', 'round_reason', 'round_index'], inplace=True)
    return ticks_df

def process_round_results(ticks_df: pd.DataFrame) -> pd.DataFrame:
    """
    Process the ticks dataframe to extract round results including winners and reasons.

    Args:
        ticks_df (pd.DataFrame): DataFrame containing tick-level data with round information.

    Returns:
        pd.DataFrame: DataFrame with round index, winner, and reason for each round.
    """
    # Capture full tick stream (including freeze/warmup) to evaluate round winners
    ticks_all = ticks_df.copy()
    
    # Filter out warmup ticks if available to avoid buggy warmup winners
    if 'is_warmup_period' in ticks_all.columns:
        ticks_all = ticks_all[ticks_all['is_warmup_period'] == False].copy()

    def last_non_zero(series):
        non_zero = series[series != 0]
        return int(non_zero.iloc[-1]) if not non_zero.empty else 0

    # Important: the win event appears after total_rounds_played increments.
    # Attribute win status/reason to the previous round index.
    ticks_all['round_for_outcome'] = ticks_all['total_rounds_played']
    win_mask = (ticks_all['round_win_status'] != 0) | (ticks_all['round_win_reason'] != 0)
    ticks_all.loc[win_mask, 'round_for_outcome'] = ticks_all.loc[win_mask, 'round_for_outcome'] - 1

    round_results = (
        ticks_all.groupby('round_for_outcome')
        .agg(round_winner=('round_win_status', last_non_zero),
            round_reason=('round_win_reason', last_non_zero))
        .reset_index()
        .rename(columns={'round_for_outcome': 'round_index'})
    )

    # Keep only rounds with a detected winner
    round_results = round_results[round_results['round_winner'] != 0].copy()

    # Backfill: ensure the final observed round has an outcome if a final win event exists
    try:
        last_round = int(ticks_df['total_rounds_played'].max())
        if last_round not in set(round_results['round_index'].tolist()):
            last_event = ticks_all.loc[win_mask].tail(1)
            if not last_event.empty:
                inferred_round = int(last_event['total_rounds_played'].iloc[0] - 1)
                if inferred_round == last_round:
                    rr = int(last_event['round_win_reason'].iloc[0]) if int(last_event['round_win_reason'].iloc[0]) != 0 else 0
                    rw = int(last_event['round_win_status'].iloc[0]) if int(last_event['round_win_status'].iloc[0]) != 0 else 0
                    if rw != 0:
                        round_results = pd.concat([round_results, pd.DataFrame([{'round_index': last_round, 'round_winner': rw, 'round_reason': rr}])], ignore_index=True)
    except Exception as _e:
        pass

    return round_results

# Parse a demo file
def parse_demo(demo_path: str):
    try:
        parser = DemoParser(demo_path=demo_path)
        header = parser.parse_header()
        header['demo_path'] = demo_path
        header['map_png_path'] = maps_background_paths.get(header['map_name'], None)
        ticks_df = parser.parse_ticks(wanted_props=['tick', 'X', 'Y', 'health', 'weapon_name', 'is_freeze_period', 'is_warmup_period','team_name', 'round_win_status', 'round_win_reason', 'bomb_planted', 'round_start_time',
        'round_end_time', 'is_bomb_planted', 'game_time', 'total_rounds_played', 'current_equip_value'])
        ticks_df.sort_values(['total_rounds_played', 'tick', 'team_name'], inplace=True)
        return ticks_df, header
    except Exception as e:
        return None, None

def _worker_standalone(demo_path):
    def fail():
        return pd.DataFrame(), [demo_path]
    
    try:
        ticks_df, header = parse_demo(demo_path)
        map_name = header.get('map_name')
        if ticks_df is None:
            return fail()

        round_results = process_round_results(ticks_df)
        ticks_df = integrate_round_results(ticks_df, round_results)
        ticks_df = finalize_ticks_dataframe(ticks_df)
        ticks_df = filter_initial_round_ticks(ticks_df)
        ticks_df = set_categorical_data_types(ticks_df)

        round_summary_df = build_round_summary(ticks_df, round_results)
        if round_summary_df is None or round_summary_df.empty:
            return fail()
        round_summary_df['map_name'] = map_name

        first = round_summary_df.iloc[0][['team_ct_current_equip_value', 'team_t_current_equip_value']]
        if first.isna().any():
            return fail()

        if first['team_ct_current_equip_value'] <= 5500 and first['team_t_current_equip_value'] <= 5500:
            return round_summary_df, []
        else:
            return fail()

    except Exception as e:
        return fail()