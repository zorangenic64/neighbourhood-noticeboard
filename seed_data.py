from datetime import datetime, timedelta
from random import choice

from werkzeug.security import generate_password_hash

from models.models import db, User, Post, Comment
from app import app


def seed():
    with app.app_context():
        db.drop_all()
        db.create_all()

        alice = User(
            username="alice",
            password_hash=generate_password_hash("Password123!"),
            security_question="Favourite dog?",
            security_answer_hash=generate_password_hash("mala"),
            default_location="Manchester"
        )

        bob = User(
            username="bob",
            password_hash=generate_password_hash("Password123!"),
            security_question="Dog?",
            security_answer_hash=generate_password_hash("mala"),
            default_location="Leeds"
        )

        db.session.add_all([alice, bob])
        db.session.commit()

        base_time = datetime.utcnow()

        sample_posts = [
            {
                "title": "Road bike for sale",
                "body": "Road bike, barely used, size M. Collection from Manchester city centre.",
                "category": "Selling",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=1)
            },
            {
                "title": "Child seat available",
                "body": "Good condition child seat available free. Pick up in Chorlton.",
                "category": "Free to Good Home",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": False,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=12)
            },
            {
                "title": "Local handyman",
                "body": "I offer general repairs and painting around the neighbourhood.",
                "category": "Services Offered",
                "location": "Manchester",
                "visibility": "members",
                "comments_enabled": True,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=23)
            },
            {
                "title": "Missing dog",
                "body": "Spotted near the canal last night. Please contact if seen.",
                "category": "Lost and Found",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=34)
            },
            {
                "title": "Community litter pick",
                "body": "Join us this Saturday morning in the park for a neighbourhood clean-up.",
                "category": "Event",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=45)
            },
            {
                "title": "Local bakery opening",
                "body": "New bakery opening next week with free samples on opening day.",
                "category": "Announcements",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": False,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=56)
            },
            {
                "title": "Couch available",
                "body": "Three-seat sofa in good condition. Free to collect from South Manchester.",
                "category": "Free to Good Home",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=67)
            },
            {
                "title": "Garden shed for sale",
                "body": "8x6 garden shed, used but solid. £60. Collection only.",
                "category": "Selling",
                "location": "Manchester",
                "visibility": "members",
                "comments_enabled": False,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=78)
            },
            {
                "title": "Lost mobile phone",
                "body": "Phone lost near the station. Please get in touch if found.",
                "category": "Lost and Found",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=89)
            },
            {
                "title": "Neighbourhood book swap",
                "body": "Bring any books you no longer need and take one home for free.",
                "category": "Event",
                "location": "Manchester",
                "visibility": "public",
                "comments_enabled": False,
                "author_id": alice.id,
                "created_at": base_time - timedelta(minutes=100)
            },
            {
                "title": "Mountain bike for sale",
                "body": "Large mountain bike in good condition. £150. Leeds area only.",
                "category": "Selling",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=111)
            },
            {
                "title": "Free moving boxes",
                "body": "I have several sturdy boxes left over from a move. Free collection.",
                "category": "Free to Good Home",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": False,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=122)
            },
            {
                "title": "Dog walking service",
                "body": "Reliable dog walker available weekdays and weekends in the local area.",
                "category": "Services Offered",
                "location": "Leeds",
                "visibility": "members",
                "comments_enabled": True,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=133)
            },
            {
                "title": "Missing keys",
                "body": "Set of house keys found near the square. Please contact if they belong to you.",
                "category": "Lost and Found",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=144)
            },
            {
                "title": "Community football match",
                "body": "Friendly neighbourhood football match on Sunday afternoon. All welcome.",
                "category": "Event",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=155)
            },
            {
                "title": "Market stall notice",
                "body": "New stall is opening in the town centre with handmade goods and local produce.",
                "category": "Announcements",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": False,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=166)
            },
            {
                "title": "Dining table free",
                "body": "Solid wooden dining table. Free to collect if you can collect it.",
                "category": "Free to Good Home",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=177)
            },
            {
                "title": "Piano for sale",
                "body": "Good quality upright piano. £300. Please message for details.",
                "category": "Selling",
                "location": "Leeds",
                "visibility": "members",
                "comments_enabled": False,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=188)
            },
            {
                "title": "Found wallet",
                "body": "Wallet found on the high street. Please contact to arrange collection.",
                "category": "Lost and Found",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": True,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=199)
            },
            {
                "title": "Street festival announcement",
                "body": "Street festival planned for next month with food, music and kids activities.",
                "category": "Announcements",
                "location": "Leeds",
                "visibility": "public",
                "comments_enabled": False,
                "author_id": bob.id,
                "created_at": base_time - timedelta(minutes=210)
            }
        ]

        db.session.add_all(
            Post(
                title=item["title"],
                body=item["body"],
                category=item["category"],
                location=item["location"],
                visibility=item["visibility"],
                comments_enabled=item["comments_enabled"],
                expires_in_days=choice((7, 14, 30)),
                author_id=item["author_id"],
                created_at=item["created_at"]
            )
            for item in sample_posts
        )
        db.session.commit()

        posts = Post.query.order_by(Post.id).all()

        comment_sets = [
            (posts[0].id, alice.id, "Manchester", "Looks good. Is it still available?", base_time - timedelta(minutes=3)),
            (posts[0].id, bob.id, "Leeds", "I’m interested, can you share more details?", base_time - timedelta(minutes=8)),
            (posts[2].id, bob.id, "Leeds", "Happy to help if needed.", base_time - timedelta(minutes=25)),
            (posts[3].id, alice.id, "Manchester", "Please let me know if you find it.", base_time - timedelta(minutes=40)),
            (posts[4].id, bob.id, "Leeds", "I’ll be there!", base_time - timedelta(minutes=49)),
            (posts[7].id, alice.id, "Manchester", "Can I collect this weekend?", base_time - timedelta(minutes=83)),
            (posts[9].id, bob.id, "Leeds", "Sounds great, count me in.", base_time - timedelta(minutes=108)),
            (posts[10].id, alice.id, "Manchester", "I’m interested, is the price negotiable?", base_time - timedelta(minutes=116)),
            (posts[11].id, bob.id, "Leeds", "I can collect it this afternoon.", base_time - timedelta(minutes=128)),
            (posts[12].id, alice.id, "Manchester", "Do you do evening walks?", base_time - timedelta(minutes=138)),
            (posts[13].id, bob.id, "Leeds", "I can help with that.", base_time - timedelta(minutes=149)),
            (posts[14].id, alice.id, "Manchester", "Would love to join.", base_time - timedelta(minutes=160)),
            (posts[16].id, bob.id, "Leeds", "Free to collect?", base_time - timedelta(minutes=182)),
            (posts[17].id, alice.id, "Manchester", "I’m interested in the piano.", base_time - timedelta(minutes=192)),
            (posts[18].id, bob.id, "Leeds", "Please contact me if you still have it.", base_time - timedelta(minutes=205)),
        ]

        db.session.add_all(
            Comment(
                body=body,
                author_id=author_id,
                post_id=post_id,
                location=location,
                created_at=created_at
            )
            for post_id, author_id, location, body, created_at in comment_sets
        )
        db.session.commit()


if __name__ == "__main__":
    seed()
