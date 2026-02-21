from collections import defaultdict
from pathlib import Path
from typing import Dict, List

import pandas as pd
from fastapi import FastAPI, Query
from pydantic import BaseModel


DATA_DIR = Path(".")
FINAL_PATH = DATA_DIR / "recommendations.parquet"
PERSONAL_PATH = DATA_DIR / "personal_als.parquet"
TOP_PATH = DATA_DIR / "top_popular.parquet"
SIMILAR_PATH = DATA_DIR / "similar.parquet"

ONLINE_HISTORY_SIZE = 50
RECENT_HISTORY_FOR_I2I = 5

app = FastAPI(title="Recsys Service", version="1.0.0")


class EventIn(BaseModel):
    user_id: int
    track_id: int


class RecOut(BaseModel):
    user_id: int
    recommendations: List[int]


online_history: Dict[int, List[int]] = defaultdict(list)
final_by_user: Dict[int, List[int]] = {}
personal_by_user: Dict[int, List[int]] = {}
top_tracks: List[int] = []
similar_by_track: Dict[int, List[int]] = {}


def _to_user_recs(
    df: pd.DataFrame, user_col: str = "user_id", item_col: str = "track_id"
) -> Dict[int, List[int]]:
    if "rank" in df.columns:
        df = df.sort_values([user_col, "rank"], ascending=[True, True])
    elif "score" in df.columns:
        df = df.sort_values([user_col, "score"], ascending=[True, False])
    elif "rank_score" in df.columns:
        df = df.sort_values([user_col, "rank_score"], ascending=[True, False])

    out: Dict[int, List[int]] = {}
    for uid, part in df.groupby(user_col):
        out[int(uid)] = part[item_col].astype(int).tolist()
    return out


def _unique_keep_order(items: List[int]) -> List[int]:
    seen = set()
    out = []
    for x in items:
        if x not in seen:
            out.append(x)
            seen.add(x)
    return out


def _load_data() -> None:
    global final_by_user, personal_by_user, top_tracks, similar_by_track

    final_df = pd.read_parquet(FINAL_PATH)
    personal_df = pd.read_parquet(PERSONAL_PATH)
    top_df = pd.read_parquet(TOP_PATH)
    similar_df = pd.read_parquet(SIMILAR_PATH)

    final_by_user = _to_user_recs(final_df)
    personal_by_user = _to_user_recs(personal_df)

    if "rank" in top_df.columns:
        top_df = top_df.sort_values("rank")
    top_tracks = top_df["track_id"].astype(int).drop_duplicates().tolist()

    similar_df = similar_df.sort_values(["track_id", "rank"], ascending=[True, True])
    similar_by_track = {}
    for tid, part in similar_df.groupby("track_id"):
        similar_by_track[int(tid)] = part["similar_track_id"].astype(int).tolist()


def _build_recommendations(user_id: int, k: int) -> List[int]:
    history = online_history.get(user_id, [])
    history_set = set(history)

    offline = final_by_user.get(user_id)
    if offline is None:
        offline = personal_by_user.get(user_id, top_tracks)

    online_candidates = []
    for tid in history[-RECENT_HISTORY_FOR_I2I:]:
        online_candidates.extend(similar_by_track.get(tid, []))
    online_candidates = _unique_keep_order(online_candidates)

    if user_id not in final_by_user and user_id not in personal_by_user:
        mixed = top_tracks
    elif not history:
        mixed = offline
    else:
        mixed = (
            offline[: int(k * 0.7)]
            + online_candidates[: int(k * 0.6)]
            + offline[int(k * 0.7) :]
        )

    mixed = [t for t in _unique_keep_order(mixed) if t not in history_set]
    if len(mixed) < k:
        tail = [t for t in top_tracks if t not in history_set and t not in set(mixed)]
        mixed.extend(tail)

    return mixed[:k]


@app.on_event("startup")
def startup() -> None:
    _load_data()


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/event")
def add_event(event: EventIn) -> Dict[str, str]:
    hist = online_history[event.user_id]
    hist.append(event.track_id)
    if len(hist) > ONLINE_HISTORY_SIZE:
        online_history[event.user_id] = hist[-ONLINE_HISTORY_SIZE:]
    return {"status": "accepted"}


@app.get("/recommendations", response_model=RecOut)
def recommendations(
    user_id: int = Query(...), k: int = Query(20, ge=1, le=100)
) -> RecOut:
    recs = _build_recommendations(user_id=user_id, k=k)
    return RecOut(user_id=user_id, recommendations=recs)
