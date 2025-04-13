"""update product

Revision ID: fb62f8a1f34e
Revises: 6a9190583470
Create Date: 2025-04-13 23:26:17.419741

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.engine.reflection import Inspector


# revision identifiers, used by Alembic.
revision = 'fb62f8a1f34e'
down_revision = '6a9190583470'
branch_labels = None
depends_on = None


def upgrade():
    # For development environment - drop and recreate tables
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Drop the product_article_link table if it exists
    if 'product_article_link' in inspector.get_table_names():
        op.drop_table('product_article_link')
    
    # Drop the product table if it exists
    if 'product' in inspector.get_table_names():
        op.drop_table('product')
    
    # Create the new product table with updated schema
    op.create_table(
        'product',
        sa.Column('id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('featured_image', sa.String(length=500), nullable=True),
        sa.Column('social_links', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create index on name and slug
    op.create_index(op.f('ix_product_name'), 'product', ['name'], unique=False)
    op.create_index(op.f('ix_product_slug'), 'product', ['slug'], unique=True)
    
    # Create the product_article_link table
    op.create_table(
        'product_article_link',
        sa.Column('product_id', sa.Integer(), nullable=True),
        sa.Column('article_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['article_id'], ['article.id'], ),
        sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
        sa.PrimaryKeyConstraint('product_id', 'article_id')
    )


def downgrade():
    # Simple downgrade - just drop tables
    conn = op.get_bind()
    inspector = Inspector.from_engine(conn)
    
    # Drop the product_article_link table if it exists
    if 'product_article_link' in inspector.get_table_names():
        op.drop_table('product_article_link')
    
    # Drop the product table if it exists
    if 'product' in inspector.get_table_names():
        op.drop_table('product')
        
    # We don't recreate the old schema since this is a development environment 