"""名前変更追跡システムのテストスクリプト"""
import logging
from member_tracker import MemberTracker

logging.basicConfig(level=logging.INFO)

# テストデータ
test_data_1 = [
    {"name": "藤田ことね", "player_id": "21032052", "rank": "12603"},
    {"name": "プレイヤーA", "player_id": "11111111", "rank": "5000"},
    {"name": "プレイヤーB", "player_id": "22222222", "rank": "8000"},
]

test_data_2 = [
    {"name": "新しい名前", "player_id": "21032052", "rank": "12500"},  # 藤田ことね→新しい名前
    {"name": "プレイヤーA", "player_id": "11111111", "rank": "4900"},
    {"name": "プレイヤーB改", "player_id": "22222222", "rank": "7800"},  # プレイヤーB→プレイヤーB改
]

print("=" * 80)
print("名前変更追跡システムのテスト")
print("=" * 80)

# 1回目の更新
print("\n【1回目: 初回登録】")
tracker = MemberTracker("test_members.json")
changes = tracker.update_members(test_data_1)
tracker.save()
print(f"登録された団員数: {len(tracker.members)}")
print(f"名前変更: {len(changes)}件")

# 2回目の更新（名前変更あり）
print("\n【2回目: 名前変更を検出】")
tracker = MemberTracker("test_members.json")
changes = tracker.update_members(test_data_2)
tracker.save()

if changes:
    print(f"\n検出された名前変更: {len(changes)}件")
    for player_id, change in changes.items():
        print(f"  ID: {player_id}")
        print(f"    旧名前: {change['old_name']}")
        print(f"    新名前: {change['new_name']}")
else:
    print("名前変更なし")

# 履歴確認
print("\n【履歴確認】")
member = tracker.get_member_by_id("21032052")
if member:
    print(f"ID: {member['player_id']}")
    print(f"現在の名前: {member['current_name']}")
    print(f"名前履歴: {member['name_history']}")

print("\n" + "=" * 80)
print("テスト完了！test_members.json を確認してください")
print("=" * 80)
