from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError
from flask import current_app

import config
from models.models import AuditLog, AuditLogRotationState, db


def write_audit_log(
    event_name,
    outcome,
    user_id=None,
    post_id=None,
    comment_id=None,
    notes=None,
):
    connection = None
    try:
        connection = db.engines["logs"].connect()
        connection.exec_driver_sql("BEGIN IMMEDIATE")

        state_table = AuditLogRotationState.__table__
        state = connection.execute(
            select(state_table).where(state_table.c.id == 1)
        ).first()

        if state is None:
            generation = 1
            rows_in_generation = 0
            connection.execute(
                state_table.insert().values(
                    id=1,
                    current_generation=generation,
                    rows_in_generation=rows_in_generation,
                )
            )
        else:
            generation = state.current_generation
            rows_in_generation = state.rows_in_generation

        if rows_in_generation >= config.MAX_LOG_SIZE:
            generation += 1
            rows_in_generation = 0

        connection.execute(
            AuditLog.__table__.insert().values(
                event_name=event_name,
                outcome=outcome,
                user_id=user_id,
                post_id=post_id,
                comment_id=comment_id,
                notes=notes,
                generation=generation,
            )
        )
        connection.execute(
            update(state_table)
            .where(state_table.c.id == 1)
            .values(
                current_generation=generation,
                rows_in_generation=rows_in_generation + 1,
            )
        )
        connection.commit()
    except SQLAlchemyError:
        if connection is not None:
            connection.rollback()
        current_app.logger.exception("Failed to write audit log event %s", event_name)
    finally:
        if connection is not None:
            connection.close()
