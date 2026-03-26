from sqlalchemy.orm import Session
from src.dal import models
from src.models import schemas
from ..core.logging import setup_logging

logger = setup_logging()

def create_rms_report(db: Session, report: schemas.RmsReportCreate):
    """
    Creates a new machine event record in the database.
    """
    try:
        logger.info(f"Creating machine event record for SN {report.sn}, event_type {report.event_type}")
        
        db_event = models.MachineEvent(
            # Metadata
            sn=report.sn,
            event_type=report.event_type,
            timestamp=report.timestamp,
            
            # RMS values
            rms_x=report.rms.x,
            rms_y=report.rms.y,
            rms_z=report.rms.z,
            rms_m=report.rms.m,
            
            # Peak values
            peak_x=report.peak.x,
            peak_y=report.peak.y,
            peak_z=report.peak.z,
            peak_m=report.peak.m,
            
            # Crest values
            crest_x=report.crest.x,
            crest_y=report.crest.y,
            crest_z=report.crest.z,
            crest_m=report.crest.m,
            
            # Impulse values
            impulse_x=report.impulse.x,
            impulse_y=report.impulse.y,
            impulse_z=report.impulse.z,
            impulse_m=report.impulse.m,
            
            # Other fields
            temperature=report.temperature,
            iso=report.iso,
        )
        
        logger.info(f"Adding event to database session for SN {report.sn}")
        db.add(db_event)
        
        logger.info(f"Committing transaction for SN {report.sn}")
        db.commit()
        
        logger.info(f"Refreshing event object for SN {report.sn}")
        db.refresh(db_event)
        
        logger.info(f"Successfully created machine event with ID {db_event.id} for SN {report.sn}")
        return db_event
        
    except Exception as e:
        logger.error(f"Failed to create machine event for SN {report.sn}: {e}")
        db.rollback()  # 确保事务回滚
        raise


def _round_to_3dp(value: float) -> float:
    """Round a float value to 3 decimal places for display"""
    return round(value, 3) if value is not None else None


def _rms_report_to_dict(report: models.MachineEvent) -> dict:
    """Convert MachineEvent to dict with triaxial values rounded to 3 decimal places"""
    result = {}
    triaxial_fields = {
        'rms_x', 'rms_y', 'rms_z', 'rms_m',
        'peak_x', 'peak_y', 'peak_z', 'peak_m',
        'crest_x', 'crest_y', 'crest_z', 'crest_m',
        'impulse_x', 'impulse_y', 'impulse_z', 'impulse_m'
    }
    
    for column in report.__table__.columns:
        value = getattr(report, column.name)
        # Round triaxial values to 3 decimal places, keep others as-is
        if column.name in triaxial_fields:
            result[column.name] = _round_to_3dp(value)
        else:
            result[column.name] = value
    
    return result


def get_rms_reports(
    db: Session,
    sn: int | None = None,
    day: str | None = None,
    start_at: str | None = None,
    end_at: str | None = None,
    limit: int = 20,
):
    query = db.query(models.MachineEvent)

    if sn is not None:
        query = query.filter(models.MachineEvent.sn == sn)

    if day is not None:
        try:
            from datetime import datetime, timedelta

            day_date = datetime.fromisoformat(day).date()
            day_start = int(datetime.combine(day_date, datetime.min.time()).timestamp() * 1000)
            day_end = int((datetime.combine(day_date, datetime.max.time()) + timedelta(microseconds=1)).timestamp() * 1000)
            query = query.filter(models.MachineEvent.timestamp >= day_start, models.MachineEvent.timestamp <= day_end)
        except Exception as exc:
            raise ValueError(f"Invalid day format '{day}', use YYYY-MM-DD") from exc

    if start_at is not None:
        try:
            from datetime import datetime

            start_ts = int(datetime.fromisoformat(start_at).timestamp() * 1000)
            query = query.filter(models.MachineEvent.timestamp >= start_ts)
        except Exception as exc:
            raise ValueError(f"Invalid start_at format '{start_at}', use ISO 8601") from exc

    if end_at is not None:
        try:
            from datetime import datetime

            end_ts = int(datetime.fromisoformat(end_at).timestamp() * 1000)
            query = query.filter(models.MachineEvent.timestamp <= end_ts)
        except Exception as exc:
            raise ValueError(f"Invalid end_at format '{end_at}', use ISO 8601") from exc

    query = query.order_by(models.MachineEvent.timestamp.desc()).limit(limit)
    results = query.all()
    return [_rms_report_to_dict(r) for r in results]
