from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr
from typing import Optional, List
from datetime import datetime


class UserBase(SQLModel):
    username: str = Field(max_length=50, index=True, unique=True)
    email: EmailStr = Field(max_length=200, index=True, unique=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    password: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    articles: List["Article"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="author")


class UserCreate(UserBase):
    password: str


class UserRead(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class CategoryBase(SQLModel):
    name: str = Field(max_length=100, index=True, unique=True)
    description: Optional[str] = None


class Category(CategoryBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    articles: List["Article"] = Relationship(back_populates="category")


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ArticleBase(SQLModel):
    title: str = Field(max_length=200)
    content: str
    published: bool = Field(default=False)
    featured_image: Optional[str] = Field(default=None, max_length=500)
    views: int = Field(default=0)
    category_id: int = Field(foreign_key="category.id")
    author_id: int = Field(foreign_key="user.id")


class Article(ArticleBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    category: Category = Relationship(back_populates="articles")
    author: User = Relationship(back_populates="articles")
    comments: List["Comment"] = Relationship(back_populates="article")


class ArticleCreate(ArticleBase):
    pass


class ArticleRead(ArticleBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ArticleUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    published: Optional[bool] = None
    featured_image: Optional[str] = None
    category_id: Optional[int] = None


class CommentBase(SQLModel):
    content: str
    article_id: int = Field(foreign_key="article.id")
    author_id: int = Field(foreign_key="user.id")


class Comment(CommentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    article: Article = Relationship(back_populates="comments")
    author: User = Relationship(back_populates="comments")


class CommentCreate(CommentBase):
    pass


class CommentRead(CommentBase):
    id: int
    created_at: datetime
    updated_at: datetime


class CommentUpdate(SQLModel):
    content: Optional[str] = None 