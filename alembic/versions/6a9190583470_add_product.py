"""add_product

Revision ID: 6a9190583470
Revises: 3b89d8314b1d
Create Date: 2025-04-13 20:28:21.548209

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision = '6a9190583470'
down_revision = '3b89d8314b1d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('product',
    sa.Column('name', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
    sa.Column('price', sa.Float(), nullable=False),
    sa.Column('slug', sqlmodel.sql.sqltypes.AutoString(length=200), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('featured_image', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('shopee_link', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('lazada_link', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('amazon_link', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('tiki_link', sqlmodel.sql.sqltypes.AutoString(length=500), nullable=True),
    sa.Column('other_links', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_product_name'), 'product', ['name'], unique=False)
    op.create_index(op.f('ix_product_slug'), 'product', ['slug'], unique=True)
    op.create_table('productarticlelink',
    sa.Column('product_id', sa.Integer(), nullable=False),
    sa.Column('article_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['article_id'], ['article.id'], ),
    sa.ForeignKeyConstraint(['product_id'], ['product.id'], ),
    sa.PrimaryKeyConstraint('product_id', 'article_id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('productarticlelink')
    op.drop_index(op.f('ix_product_slug'), table_name='product')
    op.drop_index(op.f('ix_product_name'), table_name='product')
    op.drop_table('product')
    # ### end Alembic commands ### 