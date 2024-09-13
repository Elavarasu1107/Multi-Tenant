from collections import defaultdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import and_, cast, func, select
from sqlalchemy.types import TIMESTAMP

from core.db_manager import DatabaseManager

from .models import Member, Organisation, Role, User, get_db_session
from .schemas import *

statistics = APIRouter(prefix="/api/stats", tags=["Stats"])


@statistics.get("/roles/users/count", response_model=BaseResponseSchema)
async def role_wise_users(db: DatabaseManager = Depends(get_db_session)):
    query = (
        select(Role.name.label("role"), func.count(User.id).label("count"))
        .join(Member, Role.id == Member.role_id)
        .join(User, Member.user_id == User.id)
        .group_by(Role.id)
    )

    result = await db.session.execute(query)
    user_count_by_role = result.fetchall()
    data = {x[0]: x[1] for x in user_count_by_role}
    return {"message": "Data fetched successfully", "status": "success", "data": data}


@statistics.get("/org/member/count", response_model=BaseResponseSchema)
async def organisation_wise_members(
    time_from: Optional[datetime] = Query(None, alias="from"),
    time_to: Optional[datetime] = Query(None, alias="to"),
    db: DatabaseManager = Depends(get_db_session),
):
    query = select(Organisation.name.label("name"), func.count(Member.id).label("count")).join(
        Member, Member.org_id == Organisation.id
    )

    if time_from and time_to:
        query = query.where(Member.created_at.between(time_from, time_to))

    query = query.group_by(Organisation.id)
    result = await db.session.execute(query)
    member_count_by_org = result.fetchall()
    data = {x[0]: x[1] for x in member_count_by_org}
    return {"message": "Data fetched successfully", "status": "success", "data": data}


@statistics.get("/org/roles/users/count", response_model=BaseResponseSchema)
async def organisation_and_role_wise_members(
    time_from: Optional[datetime] = Query(None, alias="from"),
    time_to: Optional[datetime] = Query(None, alias="to"),
    db: DatabaseManager = Depends(get_db_session),
):
    query = (
        select(
            Organisation.id.label("organisation_id"),
            Organisation.name.label("organisation_name"),
            Role.id.label("role_id"),
            Role.name.label("role_name"),
            func.count(User.id).label("user_count"),
        )
        .join(Member, Member.org_id == Organisation.id)
        .join(Role, Role.id == Member.role_id)
        .join(User, User.id == Member.user_id)
    )

    if time_from and time_to:
        query = query.where(User.created_at.between(time_from, time_to))

    query = query.group_by(Organisation.id, Organisation.name, Role.id, Role.name)

    result = await db.session.execute(query)
    org_role_wise_member = result.fetchall()

    data = defaultdict(lambda: defaultdict(int))
    for row in org_role_wise_member:
        org_name = row.organisation_name
        role_name = row.role_name
        user_count = row.user_count
        data[org_name][role_name] = user_count

    data = {org_name: dict(roles) for org_name, roles in data.items()}
    return {"message": "Data fetched successfully", "status": "success", "data": data}
