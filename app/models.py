from tortoise import fields, models
from tortoise.contrib.pydantic import pydantic_model_creator
from datetime import datetime


class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    password = fields.CharField(max_length=200)
    email = fields.CharField(max_length=200, unique=True)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return self.username


class Category(models.Model):
    id = fields.IntField(pk=True)
    name = fields.CharField(max_length=100, unique=True)
    description = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return self.name


class Article(models.Model):
    id = fields.IntField(pk=True)
    title = fields.CharField(max_length=200)
    content = fields.TextField()
    category = fields.ForeignKeyField('models.Category', related_name='articles')
    author = fields.ForeignKeyField('models.User', related_name='articles')
    published = fields.BooleanField(default=False)
    featured_image = fields.CharField(max_length=500, null=True)
    views = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    def __str__(self):
        return self.title


class Comment(models.Model):
    id = fields.IntField(pk=True)
    content = fields.TextField()
    article = fields.ForeignKeyField('models.Article', related_name='comments')
    author = fields.ForeignKeyField('models.User', related_name='comments')
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    
    def __str__(self):
        return f"Comment by {self.author.username} on {self.article.title}"


# Pydantic models for validation
User_Pydantic = pydantic_model_creator(User, name="User")
UserIn_Pydantic = pydantic_model_creator(User, name="UserIn", exclude_readonly=True)

Category_Pydantic = pydantic_model_creator(Category, name="Category")
CategoryIn_Pydantic = pydantic_model_creator(Category, name="CategoryIn", exclude_readonly=True)

Article_Pydantic = pydantic_model_creator(Article, name="Article")
ArticleIn_Pydantic = pydantic_model_creator(Article, name="ArticleIn", exclude_readonly=True)

Comment_Pydantic = pydantic_model_creator(Comment, name="Comment")
CommentIn_Pydantic = pydantic_model_creator(Comment, name="CommentIn", exclude_readonly=True) 