"""Local identity, session revocation and private resource ownership."""

from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "access_sessions",
        sa.Column("token_hash", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("expires_at", sa.Integer(), nullable=False),
        sa.Column("revoked", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_access_sessions_user_id", "access_sessions", ["user_id"])
    op.create_table(
        "login_throttles",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.Integer(), nullable=False),
        sa.Column("blocked_until", sa.Integer(), nullable=False),
    )
    op.create_table(
        "dataset_grants",
        sa.Column("dataset_id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), primary_key=True),
    )
    for table in ["datasets", "runs"]:
        op.add_column(table, sa.Column("owner_id", sa.String(36), nullable=True))
        op.create_index("ix_" + table + "_owner_id", table, ["owner_id"])
    op.add_column("audit_events", sa.Column("actor_id", sa.String(36), nullable=True))


def downgrade():
    op.drop_column("audit_events", "actor_id")
    for table in ["runs", "datasets"]:
        op.drop_index("ix_" + table + "_owner_id", table_name=table)
        op.drop_column(table, "owner_id")
    op.drop_table("dataset_grants")
    op.drop_table("login_throttles")
    op.drop_index("ix_access_sessions_user_id", table_name="access_sessions")
    op.drop_table("access_sessions")
    op.drop_table("users")
