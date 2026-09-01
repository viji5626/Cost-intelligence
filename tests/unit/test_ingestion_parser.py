"""
Unit Tests for Ingestion Parser and Header Normalization
"""

from backend.app.services.ingestion.models import IngestionTarget, ValidationSeverity
from backend.app.services.ingestion.parser import IngestionParser


def test_header_normalization():
    assert IngestionParser.normalize_header("Plant Code") == "plant_code"
    assert IngestionParser.normalize_header("Part No. / Item") == "part_no_item"
    assert IngestionParser.normalize_header("Total OPEX (INR)") == "total_opex_inr"


def test_column_alias_matching():
    raw_headers = ["Factory", "Month_Year", "Volume", "Power_Units", "Total_Expense"]
    col_map = IngestionParser.match_columns_to_target(raw_headers, IngestionTarget.PLANT_OPEX)
    assert col_map.get("plant_code") == "Factory"
    assert col_map.get("period") == "Month_Year"
    assert col_map.get("production_quantity") == "Volume"
    assert col_map.get("total_opex") == "Total_Expense"


def test_parse_csv_stream_plant_opex():
    csv_content = (
        "Plant,Period,Prod_Qty,Electricity_kWh,Total_OPEX\n"
        "PLANT-HAR,2024-04-01,100000,2500000,55000000\n"
        "PLANT-DHA,2024-04-01,80000,2000000,44000000\n"
        "PLANT-NEEM,2024-04-01,0,0,0\n"  # Invalid row (prod_qty = 0)
    ).encode("utf-8")

    results = list(IngestionParser.parse_csv_stream(csv_content, IngestionTarget.PLANT_OPEX))
    assert len(results) == 3
    assert results[0].severity == ValidationSeverity.VALID
    assert results[1].severity == ValidationSeverity.VALID
    assert results[2].severity == ValidationSeverity.INVALID_DATA
    assert len(results[2].errors) >= 1
