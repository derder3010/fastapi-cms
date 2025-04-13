"""
Script to generate fake data for testing the CMS
Run this script to populate the database with test data
"""

import sys
import os
from pathlib import Path

# Add the parent directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, SQLModel, create_engine
from app.models import User, Article, Category, Tag, Comment, Product, ArticleTagLink, ProductArticleLink
from app.auth.utils import get_password_hash
from app.config import settings
from app.database import engine  # Import engine directly instead of get_engine
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker()

def create_test_data():
    # Create a session using the engine
    with Session(engine) as session:
        print("Generating test data...")
        
        # Create admin user if not exists
        admin = session.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True,
                first_name="Admin",
                last_name="User"
            )
            session.add(admin)
            session.commit()
            print("- Admin user created")
        
        # Create regular users
        users = [admin]  # Start with admin
        user_count = 50
        
        for i in range(1, user_count):
            first_name = fake.first_name()
            last_name = fake.last_name()
            username = f"{first_name.lower()}{i}"
            email = f"{username}@example.com"
            
            user = User(
                username=username,
                email=email,
                password=get_password_hash("password123"),
                is_active=random.choice([True, True, True, False]),  # 75% active
                is_superuser=random.choice([False, False, False, True]),  # 25% admin
                first_name=first_name,
                last_name=last_name
            )
            session.add(user)
            users.append(user)
        
        session.commit()
        print(f"- {user_count} users created")
        
        # Create categories
        categories = []
        category_names = [
            "Technology", "Science", "Business", "Health", "Sports", 
            "Entertainment", "Politics", "Education", "Travel", "Food",
            "Fashion", "Art", "Music", "Books", "Movies"
        ]
        
        for name in category_names:
            category = Category(
                name=name,
                description=fake.paragraph(nb_sentences=3)
            )
            session.add(category)
            categories.append(category)
        
        session.commit()
        print(f"- {len(categories)} categories created")
        
        # Create tags
        tags = []
        tag_names = [
            "Python", "JavaScript", "Web Development", "AI", "Machine Learning",
            "Data Science", "Frontend", "Backend", "Mobile", "Cloud",
            "DevOps", "Security", "Database", "API", "UI/UX",
            "Blockchain", "IoT", "Augmented Reality", "Virtual Reality", "Quantum Computing",
            "Robotics", "5G", "Fintech", "Healthtech", "Edtech",
            "Gaming", "Big Data", "Networking", "Cybersecurity", "Serverless"
        ]
        
        for name in tag_names:
            tag = Tag(name=name)
            session.add(tag)
            tags.append(tag)
        
        session.commit()
        print(f"- {len(tags)} tags created")
        
        # Create articles
        articles = []
        article_count = 200
        
        for i in range(article_count):
            published = random.choice([True, True, True, False])  # 75% published
            created_days_ago = random.randint(1, 365)
            created_at = datetime.now() - timedelta(days=created_days_ago)
            updated_at = created_at + timedelta(days=random.randint(0, created_days_ago))
            
            article = Article(
                title=fake.sentence(nb_words=6).rstrip('.'),
                content='\n\n'.join(fake.paragraphs(nb=5)),
                category_id=random.choice(categories).id,
                author_id=random.choice(users).id,
                published=published,
                featured_image=None,
                slug=fake.slug(),
                created_at=created_at,
                updated_at=updated_at
            )
            session.add(article)
            articles.append(article)
        
        session.commit()
        print(f"- {article_count} articles created")
        
        # Add tags to articles
        for article in articles:
            # Each article gets 1-5 random tags
            article_tags = random.sample(tags, random.randint(1, 5))
            for tag in article_tags:
                article_tag_link = ArticleTagLink(article_id=article.id, tag_id=tag.id)
                session.add(article_tag_link)
        
        session.commit()
        print("- Added tags to articles")
        
        # Create comments
        comment_count = 500
        
        for i in range(comment_count):
            article = random.choice(articles)
            user = random.choice(users)
            created_days_ago = random.randint(1, 365)
            created_at = datetime.now() - timedelta(days=created_days_ago)
            updated_at = created_at
            
            comment = Comment(
                content=fake.paragraph(),
                article_id=article.id,
                author_id=user.id,
                created_at=created_at,
                updated_at=updated_at
            )
            session.add(comment)
        
        session.commit()
        print(f"- {comment_count} comments created")
        
        # Create products
        products = []
        product_count = 100
        
        for i in range(product_count):
            price = random.randint(10, 1000)
            social_links = {
                "website": fake.url(),
                "twitter": f"https://twitter.com/{fake.user_name()}",
                "github": f"https://github.com/{fake.user_name()}"
            }
            
            product = Product(
                name=fake.catch_phrase(),
                price=price,
                slug=fake.slug(),
                description=fake.paragraph(nb_sentences=5),
                featured_image=None,
                social_links=str(social_links).replace("'", "\"")
            )
            session.add(product)
            products.append(product)
        
        session.commit()
        print(f"- {product_count} products created")
        
        # Link products to articles
        for product in products:
            # Each product gets 1-10 random articles
            product_articles = random.sample(articles, random.randint(1, 10))
            for article in product_articles:
                product_article_link = ProductArticleLink(product_id=product.id, article_id=article.id)
                session.add(product_article_link)
        
        session.commit()
        print("- Linked products to articles")
        
        print("Test data generation complete!")


if __name__ == "__main__":
    create_test_data() 