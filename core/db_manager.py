from asyncio import current_task

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.ext.asyncio.scoping import async_scoped_session


class DatabaseSessionManager:
    def __init__(self, host, echo=False):
        self.engine = create_async_engine(
            host, pool_size=10, max_overflow=0, pool_pre_ping=False, echo=echo
        )
        self.session_maker = async_sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine, expire_on_commit=False
        )
        self.session = async_scoped_session(self.session_maker, scopefunc=current_task)

    async def close(self):
        if self.engine is None:
            raise SQLAlchemyError("DatabaseSessionManager is not initialized")
        await self.engine.dispose()


class DatabaseManager:

    def __init__(self, host: str) -> None:
        self.db = DatabaseSessionManager(host=host)
        self._model = None
        self.session = self.db.session()

    def model(self, model):
        self._model = model
        return self

    async def create(self, **payload):
        instance = self._model(**payload)
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def add(self, instance):
        self.session.add(instance)
        await self.session.commit()
        await self.session.refresh(instance)

    async def bulk_create(self, *instances):
        self.session.add_all(*instances)
        await self.session.commit()

    async def update(self, **payload):
        instance = await self.get(id=payload.get("id"))
        for k, v in payload.items():
            setattr(instance, k, v)
        await self.session.commit()
        await self.session.refresh(instance)
        return instance

    async def delete(self, **payload):
        instance = await self.get(id=payload.get("id"))
        await self.session.delete(instance)
        await self.session.commit()

    async def authenticate(self, **payload):
        username = None
        if "email" in payload:
            username = payload["email"]
        else:
            raise KeyError("email or username required to authenticate")
        user = await self.get(email=username)
        if user.verify_password(payload["password"]):
            return user
        return None

    async def get(self, **payload):
        instance = await self.session.execute(select(self._model).filter_by(**payload))
        return instance.one()[0]

    async def get_or_none(self, **payload):
        instances = await self.session.execute(select(self._model).filter_by(**payload))
        instance = instances.unique().one_or_none()
        if not instance:
            return None
        return instance[0]

    async def get_or_create(self, **payload):
        instance = await self.get_or_none(**payload)
        if instance:
            return instance
        instance = await self.create(**payload)
        return instance

    async def filter(self, **payload):
        instance_list = await self.session.execute(select(self._model).filter_by(**payload))
        instance_list = instance_list.unique().all()
        instances = [obj[0] for obj in instance_list]
        return instances

    async def all(self):
        instance_list = await self.session.execute(select(self._model))
        instance_list = instance_list.unique().all()
        instances = [obj[0] for obj in instance_list]
        return instances

    async def save(self):
        await self.session.commit()
