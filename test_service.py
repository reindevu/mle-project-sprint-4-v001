import requests
import pandas as pd

BASE_URL = "http://127.0.0.1:8000"
K = 10

def print_case(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    
def get_recs(user_id: int, k: int = K):
    r = requests.get(f"{BASE_URL}/recommendations", params={"user_id": user_id, "k": k}, timeout=30)
    r.raise_for_status()
    return r.json()

def post_event(user_id: int, track_id: int):
    r = requests.post(f"{BASE_URL}/event", json={"user_id": user_id, "track_id": track_id}, timeout=30)
    r.raise_for_status()
    return r.json()

def main():
    health = requests.get(f"{BASE_URL}/health", timeout=10)
    health.raise_for_status()
    print("health:", health.json())
    
    personal_df = pd.read_parquet("personal_als.parquet")
    top_df = pd.read_parquet("top_popular.parquet")
    
    users_with_personal = set(personal_df["user_id"].astype(int).unique())
    fallback_user = 9_999_999_999
    
    user_with_personal = int(next(iter(users_with_personal)))
    user_with_personal_online = int(next(iter(users_with_personal - {user_with_personal})))
    
    # Кейс 1: пользователь без персональных рекомендаций
    recs1 = get_recs(fallback_user, K)
    print("user_id", recs1["user_id"])
    print("n_recs", len(recs1["recommendations"]))
    print("recs", recs1["recommendations"][:10])
    
    # Кейс 2: пользователь с персональными, но без онлайн-истории
    recs2 = get_recs(user_with_personal, K)
    print("user_id:", recs2["user_id"])
    print("n_recs:", len(recs2["recommendations"]))
    print("recs:", recs2["recommendations"][:10])
    
    # Кейс 3: пользователь с персональными и онлайн-историей
    seed_tracks = top_df["track_id"].astype(int).head(3).tolist()
    for t in seed_tracks:
        resp = post_event(user_with_personal_online, t)
        print("event:", {"user_id": user_with_personal_online, "track_id": t}, "->", resp)
        
    recs3 = get_recs(user_with_personal_online, K)
    print("user_id:", recs3["user_id"])
    print("n_recs:", len(recs3["recommendations"]))
    print("recs:", recs3["recommendations"][:10])
    
if __name__ == "__main__":
    main()