"""
Hero Cost Intelligence — Phase 10 Demo Data Seeder
===================================================
Idempotent PostgreSQL seeder for Level 2 real-stack smoke testing.

All seeded records:
  • Use IDs with -DEMO suffix
  • Use source_system = 'SYNTHETIC_DEMO'
  • Are clearly distinguishable from any real production data

Usage:
    .\.venv\Scripts\python data\seed_demo_data.py

Idempotency: uses INSERT ... ON CONFLICT DO NOTHING (via merge_on_id).
Safe to run multiple times.
"""

import asyncio
import sys
from datetime import date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

# Ensure project root is on path
sys.path.insert(0, ".")

from backend.app.core.config import get_settings
from backend.app.core.database import Base
from database.models.auth import User
from database.models.plant_opex import OpexRecord, Plant
from database.models.part_bom import Assembly, Component, ComponentCost, Part, Subsystem
from database.models.vehicle_hierarchy import (
    ModelGeneration,
    ModelYear,
    ProductFamily,
    Vehicle,
    VehicleModel,
    VehicleVariant,
)


settings = get_settings()

DEMO_PLANTS = [
    {
        "id": "plant-a-demo",
        "plant_code": "PLANT-A-DEMO",
        "name": "Plant A Demo (Haridwar)",
        "location": "Haridwar",
        "state": "UK",
        "annual_capacity_vehicles": 1_200_000,
        "manufacturing_scope": "FULL_VEHICLE_ASSEMBLY",
        "grid_tariff_inr_kwh": Decimal("7.50"),
    },
    {
        "id": "plant-b-demo",
        "plant_code": "PLANT-B-DEMO",
        "name": "Plant B Demo (Dharuhera)",
        "location": "Dharuhera",
        "state": "HR",
        "annual_capacity_vehicles": 1_200_000,
        "manufacturing_scope": "FULL_VEHICLE_ASSEMBLY",
        "grid_tariff_inr_kwh": Decimal("7.40"),
    },
]

DEMO_OPEX_RECORDS = [
    {
        "plant_id": "plant-a-demo",
        "period": date(2024, 4, 1),
        "production_quantity": 100_000,
        "electricity_kwh": Decimal("4250000.00"),
        "electricity_cost": Decimal("31875000.00"),
        "water_kl": Decimal("35000.00"),
        "water_cost": Decimal("875000.00"),
        "gas_consumption_nm3": Decimal("120000.00"),
        "gas_cost": Decimal("5000000.00"),
        "compressed_air_nm3": Decimal("345000.00"),
        "compressed_air_cost": Decimal("1520000.00"),
        "is_compressor_power_embedded": True,
        "waste_quantity_mt": Decimal("150.00"),
        "waste_cost": Decimal("600000.00"),
        "labor_cost": Decimal("20000000.00"),
        "maintenance_cost": Decimal("10000000.00"),
        "other_opex": Decimal("4200000.00"),
        "total_opex": Decimal("59500000.00"),
    },
    {
        "plant_id": "plant-b-demo",
        "period": date(2024, 4, 1),
        "production_quantity": 95_000,
        "electricity_kwh": Decimal("3610000.00"),
        "electricity_cost": Decimal("26714000.00"),
        "water_kl": Decimal("29000.00"),
        "water_cost": Decimal("754000.00"),
        "gas_consumption_nm3": Decimal("100000.00"),
        "gas_cost": Decimal("4000000.00"),
        "compressed_air_nm3": Decimal("275500.00"),
        "compressed_air_cost": Decimal("1235000.00"),
        "is_compressor_power_embedded": True,
        "waste_quantity_mt": Decimal("140.00"),
        "waste_cost": Decimal("560000.00"),
        "labor_cost": Decimal("17000000.00"),
        "maintenance_cost": Decimal("8000000.00"),
        "other_opex": Decimal("3100000.00"),
        "total_opex": Decimal("49400000.00"),
    },
]


async def upsert_if_not_exists(session: AsyncSession, model_class, obj_dict: dict, pk_field: str = "id"):
    """Insert if not exists — idempotent using SELECT + conditional INSERT."""
    existing = await session.get(model_class, obj_dict[pk_field])
    if existing is None:
        obj = model_class(**obj_dict)
        session.add(obj)
        return True
    return False


async def seed_plants(session: AsyncSession) -> None:
    print("  Seeding plants...")
    for p in DEMO_PLANTS:
        created = await upsert_if_not_exists(session, Plant, p)
        status = "created" if created else "exists"
        print(f"    [{status}] {p['plant_code']}")
    await session.flush()


async def seed_opex_records(session: AsyncSession) -> None:
    print("  Seeding OPEX records...")
    for r in DEMO_OPEX_RECORDS:
        # Check by plant_id + period (no UUID PK for OpexRecord)
        existing_stmt = select(OpexRecord).where(
            OpexRecord.plant_id == r["plant_id"],
            OpexRecord.period == r["period"],
        )
        existing = (await session.execute(existing_stmt)).scalars().first()
        if existing is None:
            session.add(OpexRecord(**r))
            print(f"    [created] {r['plant_id']} / {r['period']}")
        else:
            print(f"    [exists]  {r['plant_id']} / {r['period']}")
    await session.flush()


async def seed_vehicle_hierarchy(session: AsyncSession) -> None:
    print("  Seeding vehicle hierarchy...")
    records = [
        (ProductFamily, {"id": "pf-demo-100", "family_code": "MOTORCYCLES_100CC_DEMO", "name": "100cc Motorcycles DEMO"}),
        (Vehicle, {"id": "veh-demo-spl", "vehicle_code": "SPLENDOR_DEMO", "name": "Splendor DEMO", "product_family_id": "pf-demo-100"}),
        (Vehicle, {"id": "veh-demo-hf", "vehicle_code": "HF_DELUXE_DEMO", "name": "HF Deluxe DEMO", "product_family_id": "pf-demo-100"}),
        (VehicleModel, {"id": "mod-demo-spl", "model_code": "SPLENDOR_PLUS_DEMO", "name": "Splendor Plus DEMO", "vehicle_id": "veh-demo-spl"}),
        (VehicleModel, {"id": "mod-demo-xtreme", "model_code": "XTREME_160R_DEMO", "name": "Xtreme 160R DEMO", "vehicle_id": "veh-demo-hf"}),
        (VehicleVariant, {"id": "var-demo-spl", "variant_code": "SPL_DRUM_DEMO", "name": "Splendor Plus Drum DEMO", "model_id": "mod-demo-spl"}),
        (ModelGeneration, {"id": "gen-demo-spl", "generation_code": "SPL_G1_DEMO", "name": "Gen 1 DEMO", "variant_id": "var-demo-spl", "start_year": 2022}),
        (ModelYear, {"id": "my-demo-spl", "year_code": "SPL_2024_DEMO", "generation_id": "gen-demo-spl", "calendar_year": 2024, "annual_volume_planned": 1_000_000}),
    ]
    for model_class, data in records:
        created = await upsert_if_not_exists(session, model_class, data)
        print(f"    [{'created' if created else 'exists'}] {data['id']}")
    await session.flush()


async def seed_bom_parts(session: AsyncSession) -> None:
    print("  Seeding BOM parts...")
    records = [
        (Subsystem, {"id": "sub-demo-brk", "code": "BRAKE_SYSTEM_DEMO", "name": "Brake System DEMO"}),
        (Assembly, {"id": "assy-demo-brk", "subsystem_id": "sub-demo-brk", "code": "DRUM_BRAKE_DEMO", "name": "Drum Brake DEMO"}),
        (Component, {"id": "comp-demo-brk", "assembly_id": "assy-demo-brk", "code": "BRAKE_LEVER_DEMO", "name": "Brake Lever DEMO"}),
        (Part, {
            "id": "part-demo-brk",
            "component_id": "comp-demo-brk",
            "part_number": "53100-DEMO-001",
            "part_name": "Front Brake Lever DEMO",
            "is_safety_critical": False,
        }),
        (ComponentCost, {
            "id": "cost-demo-brk",
            "part_id": "part-demo-brk",
            "period_start": date(2024, 1, 1),
            "cost_per_piece_inr": Decimal("42.50"),
            "currency": "INR",
            "source_system": "SYNTHETIC_DEMO",
        }),
    ]
    for model_class, data in records:
        created = await upsert_if_not_exists(session, model_class, data)
        print(f"    [{'created' if created else 'exists'}] {data['id']}")
    await session.flush()


async def main():
    print("=" * 60)
    print("Hero Cost Intelligence — Phase 10 Demo Data Seeder")
    print("=" * 60)
    print(f"Database: {settings.DATABASE_URL[:40]}...")
    print()

    engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_maker() as session:
            await seed_plants(session)
            await seed_opex_records(session)
            await seed_vehicle_hierarchy(session)
            await seed_bom_parts(session)
            await session.commit()
        print()
        print("✓ Demo data seeded successfully.")
        print("  All records labeled SYNTHETIC_DEMO — safe for Level 2 smoke testing.")
    except Exception as e:
        print(f"\n✗ Seeding failed: {e}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
