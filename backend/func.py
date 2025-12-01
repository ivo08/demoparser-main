import pandas as pd
from demoparser2 import DemoParser
from backend.constants import MAPS_BACKGROUND_DIR, REASON_MAP, STATUS_MAP, DEMOS_DIR
import os
from typing import List


class DemoProcessing():
    def __init__(self, demo_path: str):
        self.demo_path = demo_path
        self.header = None
        self.ticks_df = None

        if not isinstance(demo_path, str):
            raise ValueError("demo_path must be a string")
        if os.path.isfile(demo_path) is False:
            raise FileNotFoundError(f"Demo file not found: {demo_path}")
        self.parser = DemoParser(demo_path)

    @classmethod
    def get_demos_path(cls) -> List[str]:
        demos = []
        for file in os.listdir(DEMOS_DIR):
            if file.endswith(".dem"):
                demos.append(os.path.join(DEMOS_DIR, file))
        return demos

    def _remove_freeze_warmup_periods(self) -> pd.DataFrame:
        self.ticks_df = self.ticks_df[(self.ticks_df['is_freeze_period'] == False) & (
            self.ticks_df['is_warmup_period'] == False)]
        self.ticks_df.drop(
            columns=['is_freeze_period', 'is_warmup_period'], inplace=True)

    def _derive_seconds_elapsed_in_round(self) -> pd.DataFrame:
        self.ticks_df['seconds_elapsed_in_round'] = (
            self.ticks_df['game_time'] - self.ticks_df['round_start_time']).clip(lower=0)
        self.ticks_df.drop(
            columns=['round_start_time', 'game_time'], inplace=True)

    def _map_round_outcomes(self) -> pd.DataFrame:
        self.ticks_df["round_win_status_label"] = self.ticks_df["round_win_status"].map(
            STATUS_MAP).fillna("unknown")
        self.ticks_df["round_win_reason_label"] = self.ticks_df["round_win_reason"].map(
            REASON_MAP).fillna("unknown")

        # Keep round_win_status for modeling but drop the numeric reason after mapping
        self.ticks_df.drop(columns=['round_win_reason'], inplace=True)

    def _calculate_t_ct_alive_counts(self) -> pd.DataFrame:
        self.ticks_df["t_alive"] = self.ticks_df.groupby(
            "tick")["team_name"].transform(lambda x: (x == "TERRORIST").sum())
        self.ticks_df["ct_alive"] = self.ticks_df.groupby(
            "tick")["team_name"].transform(lambda x: (x == "CT").sum())
        
    def _set_target_column(self) -> pd.DataFrame:
        """
        Set target should be the end result of the round for each tick,
        even if the tick is in the middle of the round.
        """
        self.ticks_df["target"] = self.ticks_df["round_win_status"]
        self.ticks_df.drop(columns=['round_win_status'], inplace=True)

    def _get_rounds_start_end_times(self) -> List[tuple]:
        rounds = []
        round_start_tick = None
        previous_tick = None

        for tick in self.ticks_df['tick'].unique():
            if round_start_tick is None:
                round_start_tick = tick
            elif previous_tick is not None and tick != previous_tick + 1:
                rounds.append((round_start_tick, previous_tick))
                round_start_tick = tick
            previous_tick = tick

        if round_start_tick is not None and previous_tick is not None:
            rounds.append((round_start_tick, previous_tick))

        return rounds

    def preprocess_ticks(self) -> pd.DataFrame:
        self.ticks_df = self.parser.parse_ticks(wanted_props=['tick', 'X', 'Y', 'health', 'weapon_name', 'is_freeze_period', 'is_warmup_period',
                                                'team_name', 'round_win_status', 'round_win_reason', 'bomb_planted', 'round_start_time', 'is_bomb_planted', 'game_time'])

        header = self.parser.parse_header()
        header['demo_path'] = self.demo_path

        self._remove_freeze_warmup_periods()
        self._derive_seconds_elapsed_in_round()
        self._map_round_outcomes()
        self._calculate_t_ct_alive_counts()
        self._set_target_column()

        print(self._get_rounds_start_end_times(self.ticks_df))


if __name__ == "__main__":
    demos = DemoProcessing.get_demos_path()
    processor = DemoProcessing(demos[0])
    processor.preprocess_ticks()
    print(processor.ticks_df.head())