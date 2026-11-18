"""Copy legacy SQLite rows to DATABASE_URL; set SQLITE_PATH and DATABASE_URL first."""
import os
from sqlalchemy import create_engine, MetaData, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from backend.db import Base
import backend.models
source=os.environ.get('SQLITE_PATH','./data.db')
target=os.environ['DATABASE_URL']
old=create_engine('sqlite:///'+os.path.abspath(source))
new=create_engine(target)
Base.metadata.create_all(new)
old_meta=MetaData();old_meta.reflect(bind=old)
with old.connect() as src, new.begin() as dst:
    for name in old_meta.tables:
        if name not in Base.metadata.tables: continue
        old_table=old_meta.tables[name];new_table=Base.metadata.tables[name]
        for row in src.execute(select(old_table)).mappings():
            allowed={c.name for c in new_table.columns}
            values={k:v for k,v in dict(row).items() if k in allowed}
            dst.execute(new_table.insert().prefix_with('OR IGNORE'),values) if target.startswith('sqlite') else dst.execute(pg_insert(new_table).values(**values).on_conflict_do_nothing(),values)
print('Перенос завершен. Сверьте отчеты до отключения старой базы.')
