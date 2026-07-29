import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Any
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

def month_bounds_utc(
    year: int, month: int, property_timezone: str
) -> tuple[datetime, datetime]:
    local_zone = ZoneInfo(property_timezone)
    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1

    start_local = datetime(year, month, 1, tzinfo=local_zone)
    end_local = datetime(next_year, next_month, 1, tzinfo=local_zone)

    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc)

async def calculate_monthly_revenue(property_id: str, tenant_id: str, month: int, year: int, property_timezone: str, db_session=None) -> Decimal:
    """
    Calculates revenue for a specific month.
    """

    start_utc, end_utc = month_bounds_utc(year, month, property_timezone)

    logger.debug(
        f"Querying revenue for {property_id} (tenant: {tenant_id}) "
        f"from {start_utc} to {end_utc}"
    )

    # SQL Simulation (This would be executed against the actual DB)
    query = """
        SELECT SUM(total_amount) as total
        FROM reservations
        WHERE property_id = $1
        AND tenant_id = $2
        AND check_in_date >= $3
        AND check_in_date < $4
    """
    
    # In production this query executes against a database session.
    # result = await db.fetch_val(query, property_id, tenant_id, start_utc, end_utc)
    # return result or Decimal('0')
    
    return Decimal('0') # Placeholder for now until DB connection is finalized

async def calculate_total_revenue(property_id: str, tenant_id: str) -> Dict[str, Any]:
    """
    Aggregates revenue from database.
    """
    try:
        # Import database pool
        from app.core.database_pool import DatabasePool
        
        # Initialize pool if needed
        db_pool = DatabasePool()
        await db_pool.initialize()
        
        if db_pool.session_factory:
            async with db_pool.get_session() as session:
                # Use SQLAlchemy text for raw SQL
                from sqlalchemy import text
                
                query = text("""
                    SELECT 
                        property_id,
                        SUM(total_amount) as total_revenue,
                        COUNT(*) as reservation_count,
                        currency
                    FROM reservations 
                    WHERE property_id = :property_id AND tenant_id = :tenant_id
                    GROUP BY property_id, currency
                """)
                
                result = await session.execute(query, {
                    "property_id": property_id, 
                    "tenant_id": tenant_id
                })
                rows = result.fetchall()

                if len(rows) > 1:
                    raise ValueError(
                        f"Multiple currencies for {property_id}/{tenant_id}: "
                        f"{[r.currency for r in rows]}"
                    )

                row = rows[0] if rows else None
                
                if row:
                    total_revenue = Decimal(str(row.total_revenue))
                    currency = str(row.currency)
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": str(total_revenue),
                        "currency": currency, 
                        "count": row.reservation_count
                    }
                else:
                    # No reservations found for this property
                    return {
                        "property_id": property_id,
                        "tenant_id": tenant_id,
                        "total": "0.00",
                        "currency": "USD",
                        "count": 0
                    }
        else:
            raise Exception("Database pool not available")
            
    except Exception:
        logger.exception(
            f"Revenue query failed for {property_id} (tenant: {tenant_id})"
        )
        raise
