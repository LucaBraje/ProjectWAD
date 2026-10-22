
from app import app, db, Player

with app.app_context():
    count = Player.query.count()

    print(f"Deleting {count} existing players...")

    db.session.query(Player).delete()
    db.session.commit()

    print("All old players deleted successfully!")
