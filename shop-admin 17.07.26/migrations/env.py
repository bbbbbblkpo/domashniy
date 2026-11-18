import os
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
from backend.db import Base
from backend import models
config=context.config
# This repository's minimal alembic.ini does not define logging sections.
target_metadata=Base.metadata
def run_migrations_offline():
    context.configure(url=os.getenv('DATABASE_URL',config.get_main_option('sqlalchemy.url')),target_metadata=target_metadata,literal_binds=True,compare_type=True)
    with context.begin_transaction():context.run_migrations()
def run_migrations_online():
    section=config.get_section(config.config_ini_section);section['sqlalchemy.url']=os.getenv('DATABASE_URL',section['sqlalchemy.url'])
    connectable=engine_from_config(section,prefix='sqlalchemy.',poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection,target_metadata=target_metadata,compare_type=True)
        with context.begin_transaction():context.run_migrations()
run_migrations_offline() if context.is_offline_mode() else run_migrations_online()
