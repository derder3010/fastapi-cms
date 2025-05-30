from sqlmodel import SQLModel, Field, Relationship
from pydantic import EmailStr
from typing import Optional, List
from datetime import datetime
import json
import uuid
from uuid import UUID


class UserBase(SQLModel):
    username: str = Field(max_length=50, index=True, unique=True)
    email: EmailStr = Field(max_length=200, index=True, unique=True)
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)


class User(UserBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    password: str = Field(max_length=200)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    articles: List["Article"] = Relationship(back_populates="author")
    comments: List["Comment"] = Relationship(back_populates="author")
    logs: List["SystemLog"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserRead(UserBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class CategoryBase(SQLModel):
    name: str = Field(max_length=100, index=True, unique=True)
    description: Optional[str] = None
    slug: Optional[str] = Field(default=None, max_length=100, index=True, unique=True)


class Category(CategoryBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    articles: List["Article"] = Relationship(back_populates="category")


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None


class ArticleBase(SQLModel):
    title: str = Field(max_length=200)
    content: str
    published: bool = Field(default=False)
    featured_image: Optional[str] = Field(default=None, max_length=500)
    excerpt: Optional[str] = None
    footer_content: Optional[str] = None
    views: int = Field(default=0)
    category_id: UUID = Field(foreign_key="category.id")
    author_id: UUID = Field(foreign_key="user.id")
    slug: Optional[str] = Field(default=None, max_length=200, index=True, unique=True)


class ArticleTagLink(SQLModel, table=True):
    article_id: Optional[UUID] = Field(
        default=None, foreign_key="article.id", primary_key=True
    )
    tag_id: Optional[UUID] = Field(
        default=None, foreign_key="tag.id", primary_key=True
    )


class ProductArticleLink(SQLModel, table=True):
    product_id: Optional[UUID] = Field(
        default=None, foreign_key="product.id", primary_key=True
    )
    article_id: Optional[UUID] = Field(
        default=None, foreign_key="article.id", primary_key=True
    )


class Article(ArticleBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    category: Category = Relationship(back_populates="articles")
    author: User = Relationship(back_populates="articles")
    comments: List["Comment"] = Relationship(back_populates="article")
    tags: List["Tag"] = Relationship(back_populates="articles", link_model=ArticleTagLink)
    products: List["Product"] = Relationship(back_populates="articles", link_model=ProductArticleLink)


class ArticleCreate(ArticleBase):
    pass


class ArticleRead(ArticleBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    category: Optional["CategoryRead"] = None
    author: Optional["UserRead"] = None
    tags: List["TagRead"] = []
    products: List["ProductRead"] = []

    class Config:
        from_attributes = True


class ArticleUpdate(SQLModel):
    title: Optional[str] = None
    content: Optional[str] = None
    published: Optional[bool] = None
    featured_image: Optional[str] = None
    excerpt: Optional[str] = None
    footer_content: Optional[str] = None
    category_id: Optional[UUID] = None
    slug: Optional[str] = None


class CommentBase(SQLModel):
    content: str
    article_id: UUID = Field(foreign_key="article.id")
    author_id: UUID = Field(foreign_key="user.id")


class Comment(CommentBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    article: Article = Relationship(back_populates="comments")
    author: User = Relationship(back_populates="comments")


class CommentCreate(CommentBase):
    pass


class CommentRead(CommentBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class CommentUpdate(SQLModel):
    content: Optional[str] = None


class TagBase(SQLModel):
    name: str = Field(max_length=50, index=True, unique=True)
    slug: Optional[str] = Field(default=None, max_length=50, index=True, unique=True)


class Tag(TagBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    articles: List["Article"] = Relationship(back_populates="tags", link_model=ArticleTagLink)


class TagCreate(TagBase):
    pass


class TagRead(TagBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TagUpdate(SQLModel):
    name: Optional[str] = None


class ProductBase(SQLModel):
    name: str = Field(max_length=200, index=True)
    price: int = Field(default=0)
    slug: str = Field(max_length=200, index=True, unique=True)
    description: Optional[str] = None
    featured_image: Optional[str] = Field(default=None, max_length=500)
    social_links: Optional[str] = Field(default=None)  # JSON string with format {"name": "link"}


class Product(ProductBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})
    
    # Relationships
    articles: List["Article"] = Relationship(back_populates="products", link_model=ProductArticleLink)


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    @property
    def parsed_social_links(self) -> Optional[dict]:
        """Return social_links as a parsed JSON object if it exists."""
        if not self.social_links:
            return None
        return json.loads(self.social_links)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Product Name",
                "price": 1000,
                "slug": "product-name",
                "description": "Product description",
                "featured_image": "https://example.com/image.jpg",
                "social_links": '{"facebook": "https://facebook.com/product", "twitter": "https://twitter.com/product"}',
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }


class ProductUpdate(SQLModel):
    name: Optional[str] = None
    price: Optional[int] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    featured_image: Optional[str] = None
    social_links: Optional[str] = None


class ProductReadWithParsedLinks(SQLModel):
    id: UUID
    name: str
    price: int
    slug: str
    description: Optional[str] = None
    featured_image: Optional[str] = None
    social_links: Optional[dict] = None  # This will be filled with parsed links
    created_at: datetime
    updated_at: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "name": "Product Name",
                "price": 1000,
                "slug": "product-name",
                "description": "Product description",
                "featured_image": "https://example.com/image.jpg",
                "social_links": {"facebook": "https://facebook.com/product", "twitter": "https://twitter.com/product"},
                "created_at": "2023-01-01T00:00:00",
                "updated_at": "2023-01-01T00:00:00"
            }
        }


class SystemLogBase(SQLModel):
    action: str
    details: Optional[str] = None
    user_id: UUID = Field(foreign_key="user.id")
    ip_address: Optional[str] = None


class SystemLog(SystemLogBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: User = Relationship(back_populates="logs")


class SystemLogCreate(SystemLogBase):
    pass


class SystemLogRead(SystemLogBase):
    id: UUID
    created_at: datetime


class SystemSettingsBase(SQLModel):
    key: str = Field(max_length=100, index=True, unique=True)
    value: str
    description: Optional[str] = None


class SystemSettings(SystemSettingsBase, table=True):
    id: Optional[UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow, sa_column_kwargs={"onupdate": datetime.utcnow})


class SystemSettingsCreate(SystemSettingsBase):
    pass


class SystemSettingsRead(SystemSettingsBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class SystemSettingsUpdate(SQLModel):
    value: Optional[str] = None
    description: Optional[str] = None 