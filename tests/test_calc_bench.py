"""The U102 calculation benchmark (bench/calc200/cases.py, 237 cases) runs in CI: every value must match
its independent source (NIST, APHA, IUPAC, worked by hand), every impossible input must be refused, and
every question that isn't a calculation must be left alone."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))


def test_every_calculation_case_passes(tmp_path):
    import calc_bench
    assert calc_bench.main(["--out", str(tmp_path / "calc.json")]) == 0


def test_the_benchmark_is_at_least_200_cases_and_covers_refusals():
    sys.path.insert(0, str(ROOT / "bench" / "calc200"))
    from cases import CASES
    assert len(CASES) >= 200
    assert sum(c[1] == "REFUSE" for c in CASES) >= 8 and sum(c[1] is None for c in CASES) >= 10


def test_each_calculation_records_its_implementation_version():
    from cursiv_engine.core import calc, selfknow
    record = calc.work_out("Convert 412 uS/cm at 18 C to specific conductance at 25 C").record()
    assert record["version"] == selfknow.VERSION and record["tool"] == "conductance_25"
