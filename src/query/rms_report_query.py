from ..dal import crud
from ..dal.database import SessionLocal


def query_rms_reports(
    sn: int | None = None,
    page_size: int = 20,
    curr_page: int = 1,
) -> dict:
    if page_size <= 0:
        raise ValueError('page_size must be greater than 0')
    if curr_page <= 0:
        raise ValueError('curr_page must be greater than 0')

    db_session = SessionLocal()
    try:
        items, total = crud.get_rms_reports_paginated(
            db=db_session,
            sn=sn,
            page_size=page_size,
            curr_page=curr_page,
        )
        return {
            'items': items,
            'total': total,
            'page_size': page_size,
            'curr_page': curr_page,
        }
    finally:
        db_session.close()
