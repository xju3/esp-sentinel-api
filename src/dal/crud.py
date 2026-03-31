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
        # logger.info(f"Creating rms report record for SN {report.sn}, event_type {report.event_type}")
        
        db_event = models.MachineEvent(
            # Metadata
            sn=report.sn,
            event_type=report.event_type,
            
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
        
        # logger.info(f"Adding event to database session for SN {report.sn}")
        db.add(db_event)
        
        # logger.info(f"Committing transaction for SN {report.sn}")
        db.commit()
        
        # logger.info(f"Refreshing event object for SN {report.sn}")
        db.refresh(db_event)
        
        # logger.info(f"Successfully created machine event with ID {db_event.id} for SN {report.sn}")
        return db_event
        
    except Exception as e:
        logger.error(f"Failed to create machine event for SN {report.sn}: {e}")
        db.rollback()  # 确保事务回滚
        raise


def create_machine_status(db: Session, status: schemas.MachineStatusCreate):
    """
    Creates a new machine status record in the database.
    """
    try:
        # logger.info(f"Creating machine status record for SN {status.sn}, event_type {status.event_type}")

        db_status = models.MachineStatusEvent(
            sn=status.sn,
            event_type=status.event_type,
            x=status.rms.x,
            y=status.rms.y,
            z=status.rms.z,
            m=status.rms.m,
            st=status.st,
        )

        db.add(db_status)
        db.commit()
        db.refresh(db_status)
        # logger.info(f"Successfully created machine status with ID {db_status.id} for SN {status.sn}")
        return db_status

    except Exception as e:
        logger.error(f"Failed to create machine status for SN {status.sn}: {e}")
        db.rollback()
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


def _machine_status_to_dict(status: models.MachineStatusEvent) -> dict:
    result = {}
    for column in status.__table__.columns:
        result[column.name] = getattr(status, column.name)
    return result


def get_rms_reports_paginated(
    db: Session,
    sn: int | None = None,
    page_size: int = 20,
    curr_page: int = 1,
) -> tuple[list[dict], int]:
    query = db.query(models.MachineEvent)

    if sn is not None:
        query = query.filter(models.MachineEvent.sn == sn)
    total = query.count()
    offset = (curr_page - 1) * page_size

    results = (
        query.order_by(models.MachineEvent.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return ([_rms_report_to_dict(r) for r in results], total)


def get_machine_status_events(
    db: Session,
    sn: int | None = None,
    page_size: int = 20,
    curr_page: int = 1,
) -> tuple[list[dict], int]:
    query = db.query(models.MachineStatusEvent)

    if sn is not None:
        query = query.filter(models.MachineStatusEvent.sn == sn)

    total = query.count()
    offset = (curr_page - 1) * page_size

    results = (
        query.order_by(models.MachineStatusEvent.id.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return ([_machine_status_to_dict(r) for r in results], total)
