from datetime import datetime, timedelta
from random import choice, randint

from werkzeug.security import generate_password_hash

from models.models import db, User, Post, Comment, PostPick
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
            default_location="Manchester",
            status="active"
        )

        bob = User(
            username="bob",
            password_hash=generate_password_hash("Password123!"),
            security_question="Favourite dog?",
            security_answer_hash=generate_password_hash("mala"),
            default_location="Leeds",
            status="active"
        )

        jane = User(
            username="jane",
            password_hash=generate_password_hash("Password123!"),
            security_question="Favourite dog?",
            security_answer_hash=generate_password_hash("mala"),
            default_location="Sheffield",
            status="active"
        )

        john = User(
            username="john",
            password_hash=generate_password_hash("Password123!"),
            security_question="Favourite dog?",
            security_answer_hash=generate_password_hash("mala"),
            default_location="Watford",
            status="active"
        )

        peter = User(
            username="peter",
            password_hash=generate_password_hash("Password123!"),
            security_question="Favourite dog?",
            security_answer_hash=generate_password_hash("mala"),
            default_location="London",
            status="active"
        )

        db.session.add_all([alice, bob, jane, john, peter])
        db.session.commit()

        base_time = datetime.utcnow()

        users = [
            alice,
            bob,
            jane,
            john,
            peter
        ]

        locations = [
            "Manchester",
            "Leeds",
            "Sheffield",
            "Watford",
            "London"
        ]


        categories = [
            "Event",
            "Services Offered",
            "Lost and Found",
            "Free to Good Home",
            "Selling",
            "Announcements"
        ]

        titles = [
            "Road bike for sale",
            "Missing black cat",
            "Community clean up",
            "Garden furniture available",
            "Plumber available weekends",
            "Found set of keys",
            "Free books",
            "Street food event",
            "Neighbourhood watch meeting",
            "Laptop for sale",
            "Lost wallet",
            "Dog walking service",
            "Local tutor available",
            "Coffee morning",
            "Charity bake sale",
        ]

        bodies = [
            "Item available immediately. Please contact me if interested.",
            "Recently found in the local area and hoping to locate the owner.",
            "Community event planned for this weekend with refreshments available.",
            "Offering services locally with flexible availability weekdays and weekends.",
            "Clearing out household items and would prefer they go to a good home.",
            "Looking for volunteers to help with a neighbourhood project.",
            "Selling due to lack of use. Happy to answer questions.",
        ]



        posts = []

        for i in range(80):

            author = choice(users)

            post = Post(
                title=choice(titles),
                body=" ".join([choice(bodies)] * choice([1, 2, 3, 4])),
                category=choice(categories),
                location=choice(locations),
                visibility=choice([
                    "public",
                    "members"
                ]),
                comments_enabled=choice([
                    True,
                    False
                ]),
                expires_in_days=choice([
                    7,
                    14,
                    30
                ]),
                author_id=author.id,
                created_at=base_time - timedelta(
                    minutes=randint(1,30000)
                )
            )

            posts.append(post)


        db.session.add_all(posts)
        db.session.commit()


        all_posts = Post.query.order_by(Post.id).all()

        comments = []

        for post in all_posts:

            if not post.comments_enabled:
                continue

            count = choice([0,1,2,3])

            for _ in range(count):

                commenter = choice(users)

                comments.append(
                    Comment(
                        body=choice([
                            "Looks useful.",
                            "I am interested.",
                            "Can you provide more details?",
                            "Please message me.",
                            "I would like to attend.",
                            "Still available?",
                            "Thank you for sharing."
                        ]),
                        author_id=commenter.id,
                        post_id=post.id,
                        location=commenter.default_location,
                        created_at=post.created_at + timedelta(
                                   minutes=choice([5,20,60,120])
                                )
                    )
                )


        db.session.add_all(comments)
        db.session.commit()

        all_posts = Post.query.all()

        for post in all_posts[:10]:

            if post.author_id != alice.id:

                db.session.add(
                    PostPick(
                        user_id=alice.id,
                        post_id=post.id
                    )
                )

        for post in all_posts[10:20]:

            if post.author_id != jane.id:

                db.session.add(
                    PostPick(
                        user_id=jane.id,
                        post_id=post.id
                    )
                )

        db.session.commit() 

if __name__ == "__main__":
    seed()