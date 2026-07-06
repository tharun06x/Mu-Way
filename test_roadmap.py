from data_loader import DataLoader
from roadmap_app import generate_roadmap
user_data, task_data, _ = DataLoader().load_all()
res = generate_roadmap("u1", "u1", "Full Stack Developer", user_data, task_data)
weeks = res["roadmap"].get("roadmap_weeks", [])
print("Total Weeks:", len(weeks))
for w in weeks[:3]:
    print("\nWeek", w["week"])
    for t in w["tasks"]:
        print(f"  - [{t['domain']}] {t['task_name']} (Diff: {t['difficulty_level']}, Score: {t['score']})")
