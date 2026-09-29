from app import app
from models.models import db, Post, User
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta

with app.app_context():

    db.drop_all()
    db.create_all()

    # Create test users
    user1 = User(
        username="john",
        password_hash=generate_password_hash("password123"),
        security_question="What is my favorite colour?",
        security_answer_hash=generate_password_hash("blue"),
        created_at=datetime.utcnow()
    )   

    user2 = User(
        username="mary",
        password_hash=generate_password_hash("password123"),
        security_question="What is my favorite colour?",
        security_answer_hash=generate_password_hash("pink"),
        created_at=datetime.utcnow()
    )

    db.session.add_all([user1, user2])
    db.session.commit()

    print("user1.id =", user1.id)
    print("user2.id =", user2.id)


    now = datetime.utcnow()

    two_weeks_ago = now - timedelta(days=14)
    ten_days_ago = now - timedelta(days=10)
    last_week = now - timedelta(days=7)
    five_days_ago = now - timedelta(days=5)
    three_days_ago = now - timedelta(days=3)
    yesterday = now - timedelta(days=1)
    today_morning = now.replace(hour=9, minute=15, second=0, microsecond=0)
    today_afternoon = now.replace(hour=14, minute=30, second=0, microsecond=0)
    today_evening = now.replace(hour=19, minute=45, second=0, microsecond=0)



    # Create sample posts
    posts = [

        Post(
            title="Village Christmas Fair",
            body="The annual fair is on Saturday. Volunteers still needed.",
            category="Event",
            visibility="public",
            author_id=user1.id,
            created_at=two_weeks_ago
        ),

        Post(
            title="Lost Black Cat",
            body="Missing since Tuesday evening near the village green.",
            category="Lost and Found",
            visibility="public",
            author_id=user2.id,
            created_at=ten_days_ago
        ),

        Post(
            title="Free Sofa",
            body="Brown leather sofa available. Collection only.",
            category="Free to Good Home",
            visibility="public",
            author_id=user1.id,
            created_at=last_week
        ),

        Post(
            title="Lawn Mowing Service",
            body="Reliable garden maintenance available weekends.",
            category="Services Offered",
            visibility="public",
            author_id=user2.id,
            created_at=five_days_ago
        ),

        Post(
            title="Community Watch Meeting",
            body="Members meeting next week.",
            category="Announcements",
            visibility="members",
            author_id=user1.id,
            created_at=three_days_ago
        ),

        Post(
            title="Babysitting Available",
            body="Experienced babysitter available evenings and weekends.",
            category="Services Offered",
            visibility="public",
            author_id=user2.id,
            created_at=yesterday
        ),

        Post(
            title="Garden Tools Giveaway",
            body="Several spare gardening tools free to collect.",
            category="Free to Good Home",
            visibility="public",
            author_id=user1.id,
            created_at=today_morning
        ),

        Post(
            title="Neighbourhood Coffee Morning",
            body="Join us at the community hall this Friday.",
            category="Event",
            visibility="public",
            author_id=user2.id,
            created_at=today_afternoon
        ),

        Post(
            title="Bike for Sale",
            body="Adult mountain bike in excellent condition.",
            category="Selling",
            visibility="public",
            author_id=user1.id,
            created_at=today_evening
        ),

        Post(
            title="Road Closure Notice",
            body="High Street will be closed for repairs on Monday.",
            category="Announcements",
            visibility="public",
            author_id=user2.id,
            created_at=now
        )

    ]

    db.session.add_all(posts)
    db.session.commit()

    print("Database seeded.")
    print("Test users created:")
    print("john / password123")
    print("mary / password123")
