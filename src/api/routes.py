from fastapi import APIRouter, HTTPException

from ..core.logging import setup_logging
from ..query import query_machine_status_events, query_rms_reports

logger = setup_logging()
router = APIRouter()


@router.get("/machine-state")
async def machine_state(
    sn: int | None = None,
    page_size: int = 20,
    curr_page: int = 1,
):
    try:
        return query_machine_status_events(
            sn=sn,
            page_size=page_size,
            curr_page=curr_page,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Error querying machine state: {exc}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from exc


@router.get("/rms-report")
async def rms_report(
    sn: int | None = None,
    page_size: int = 20,
    curr_page: int = 1,
):
    try:
        return query_rms_reports(
            sn=sn,
            page_size=page_size,
            curr_page=curr_page,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.error(f"Error querying rms report: {exc}")
        raise HTTPException(status_code=500, detail="Internal Server Error") from exc
