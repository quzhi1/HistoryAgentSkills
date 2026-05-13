#!/usr/bin/env python3
"""Resolve historical Chinese placenames to present administrative units.

The resolver uses CHGIS/TGAZ for the historical placename record and a modern
administrative boundary dataset for point-in-polygon reverse lookup. It maps the
TGAZ point, usually a seat or representative point, not the full historical
jurisdiction.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Protocol, Sequence, Tuple

import requests


TGAZ_BASE_URL = os.environ.get("TGAZ_BASE_URL", "https://chgis.hudci.org/tgaz").rstrip("/")
try:
    TIMEOUT = int(os.environ.get("TGAZ_TIMEOUT", "30"))
except ValueError:
    TIMEOUT = 30

MIN_TGAZ_YEAR = -222
MAX_TGAZ_YEAR = 1911
MAX_PLACE_NAME_LENGTH = 64
PLACE_NAME_PATTERN = re.compile(r"^[\w\s\-\u4e00-\u9fff·'’().（）]+$", re.UNICODE)
TGAZ_ID_PATTERN = re.compile(r"hvd_\d+")
STATUS_RESOLVED = "resolved"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_NOT_FOUND = "not_found"
STATUS_OUT_OF_RANGE = "out_of_range"
STATUS_NO_COORDINATE = "no_coordinate"


class PlaceResolverError(ValueError):
    """Raised for input, API, or boundary data problems."""


class TgazClient(Protocol):
    """Small protocol for tests and alternate TGAZ clients."""

    def search(self, name: str, year: Optional[int] = None, feature_type: Optional[str] = None) -> Any:
        """Return the JSON body from the TGAZ faceted search endpoint."""

    def get_by_id(self, sys_id: str) -> Any:
        """Return the JSON body from the TGAZ canonical placename endpoint."""


@dataclass
class HistoricalPlace:
    """A normalized TGAZ placename candidate."""

    sys_id: str = ""
    primary_name: str = ""
    names: List[str] = field(default_factory=list)
    feature_type: str = ""
    feature_type_en: str = ""
    begin_year: Optional[int] = None
    end_year: Optional[int] = None
    longitude: Optional[float] = None
    latitude: Optional[float] = None
    parent: str = ""
    present_location: str = ""
    data_source: str = ""
    source_note: str = ""
    raw: Mapping[str, Any] = field(default_factory=dict)

    @property
    def has_coordinate(self) -> bool:
        return self.longitude is not None and self.latitude is not None

    def is_active(self, year: Optional[int]) -> bool:
        if year is None:
            return True
        if self.begin_year is not None and year < self.begin_year:
            return False
        if self.end_year is not None and year > self.end_year:
            return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.sys_id,
            "name": self.primary_name,
            "names": self.names,
            "feature_type": self.feature_type,
            "feature_type_en": self.feature_type_en,
            "begin_year": self.begin_year,
            "end_year": self.end_year,
            "longitude": self.longitude,
            "latitude": self.latitude,
            "parent": self.parent,
            "present_location": self.present_location,
            "data_source": self.data_source,
            "source_note": _truncate(self.source_note, 400),
        }


@dataclass
class BoundaryRecord:
    """One modern administrative boundary record."""

    name: str
    level: str
    province: str = ""
    city: str = ""
    district: str = ""
    adcode: str = ""
    source: str = ""
    path: Optional[Path] = None
    geometry: Optional[Mapping[str, Any]] = None
    bbox: Optional[Tuple[float, float, float, float]] = None

    def ensure_loaded(self) -> None:
        if self.geometry is not None:
            if self.bbox is None:
                self.bbox = _geometry_bbox(self.geometry)
            return
        if not self.path:
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            return
        geometry = _select_geojson_geometry(data, self.adcode, self.name)
        if geometry:
            self.geometry = geometry
            self.bbox = _geometry_bbox(geometry)

    def contains(self, longitude: float, latitude: float) -> bool:
        self.ensure_loaded()
        if not self.geometry:
            return False
        if self.bbox and not _point_in_bbox(longitude, latitude, self.bbox):
            return False
        return _point_in_geometry(longitude, latitude, self.geometry)

    def rank(self) -> int:
        value = self.level.lower()
        if value in {"区县", "县", "district", "county", "xian", "4"}:
            return 4
        if value in {"市", "city", "prefecture", "3"}:
            return 3
        if value in {"省", "province", "sheng", "2"}:
            return 2
        if value in {"国", "country", "1"}:
            return 1
        return 0


class TgazHttpClient:
    """HTTP client for the read-only CHGIS/TGAZ API."""

    def __init__(self, base_url: str = TGAZ_BASE_URL, timeout: int = TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        if not self.base_url.startswith("https://"):
            raise PlaceResolverError("TGAZ_BASE_URL 必须使用 HTTPS")

    def search(self, name: str, year: Optional[int] = None, feature_type: Optional[str] = None) -> Any:
        params: Dict[str, Any] = {"fmt": "json", "n": name}
        if year is not None:
            params["yr"] = str(year)
        if feature_type:
            params["ftyp"] = feature_type
        return self._get_json(f"{self.base_url}/placename", params=params)

    def get_by_id(self, sys_id: str) -> Any:
        if not TGAZ_ID_PATTERN.fullmatch(sys_id):
            raise PlaceResolverError("TGAZ ID 格式无效")
        return self._get_json(f"{self.base_url}/placename/json/{sys_id}", params=None)

    def _get_json(self, url: str, params: Optional[Mapping[str, Any]]) -> Any:
        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, params=params, timeout=self.timeout)
                response.raise_for_status()
                return json.loads(response.text, strict=False)
            except requests.exceptions.Timeout:
                if attempt < max_attempts:
                    continue
                raise PlaceResolverError("TGAZ 查询超时") from None
            except requests.exceptions.RequestException as exc:
                raise PlaceResolverError(f"TGAZ 查询失败: {exc}") from exc
            except ValueError as exc:
                raise PlaceResolverError("TGAZ 返回了非 JSON 响应") from exc


class ModernBoundaryResolver:
    """Reverse geocode a WGS84-like point into modern administrative boundaries."""

    def __init__(self, records: Sequence[BoundaryRecord]):
        self.records = list(records)

    @classmethod
    def from_cnmaps_data(cls) -> "ModernBoundaryResolver":
        try:
            data_root = Path(str(resources.files("cnmaps_data") / "data"))
        except ModuleNotFoundError as exc:
            raise PlaceResolverError("缺少 cnmaps-data，请运行 ./setup_venv.sh") from exc

        records = _load_cnmaps_records(data_root)
        if not records:
            raise PlaceResolverError("未能从 cnmaps-data 读取现代行政区边界")
        return cls(records)

    def reverse_geocode(self, longitude: float, latitude: float) -> Optional[Dict[str, Any]]:
        matches = [record for record in self.records if record.contains(longitude, latitude)]
        if not matches:
            return None
        matches.sort(key=lambda record: record.rank(), reverse=True)
        best = matches[0]

        province = best.province or _name_for_rank(matches, 2)
        city = best.city or _name_for_rank(matches, 3)
        district = best.district or _name_for_rank(matches, 4)
        if best.rank() == 2 and not province:
            province = best.name
        if best.rank() == 3 and not city:
            city = best.name
        if best.rank() == 4 and not district:
            district = best.name

        return {
            "province": province or None,
            "city": city or None,
            "district": district or None,
            "adcode": best.adcode or None,
            "matched_level": best.level or None,
            "matched_name": best.name or None,
            "source": best.source or None,
        }


def resolve_place(
    name: str,
    year: Optional[int] = None,
    feature_type: Optional[str] = None,
    tgaz_client: Optional[TgazClient] = None,
    boundary_resolver: Optional[ModernBoundaryResolver] = None,
    max_candidates: int = 5,
) -> Dict[str, Any]:
    """Resolve one historical placename to a present administrative unit."""

    normalized_name = validate_place_name(name)
    checked_year = validate_year(year)
    result: Dict[str, Any] = {
        "query": {
            "name": normalized_name,
            "year": checked_year,
            "feature_type": feature_type,
        },
        "status": STATUS_NOT_FOUND,
        "best_match": None,
        "candidates": [],
        "modern_administration": None,
        "note": "",
    }

    if year is not None and checked_year is None:
        result["status"] = STATUS_OUT_OF_RANGE
        result["note"] = f"TGAZ 历史记录年份范围为 {MIN_TGAZ_YEAR} 至 {MAX_TGAZ_YEAR}"
        return result

    client = tgaz_client or TgazHttpClient()
    raw_results = client.search(normalized_name, year=checked_year, feature_type=feature_type)
    records = _records_from_response(raw_results)
    candidates = [_normalize_tgaz_record(record) for record in records]
    candidates = [candidate for candidate in candidates if candidate.primary_name or candidate.names or candidate.sys_id]

    enriched: List[HistoricalPlace] = []
    for candidate in candidates:
        if candidate.sys_id and not candidate.has_coordinate:
            try:
                detailed = _normalize_tgaz_record(client.get_by_id(candidate.sys_id))
            except PlaceResolverError:
                detailed = candidate
            candidate = _merge_place_records(candidate, detailed)
        enriched.append(candidate)

    candidates = [candidate for candidate in enriched if candidate.is_active(checked_year)]
    if not candidates:
        result["status"] = STATUS_NOT_FOUND
        result["note"] = "TGAZ 未返回可用候选"
        return result

    ranked = sorted(candidates, key=lambda candidate: _candidate_score(candidate, normalized_name, checked_year), reverse=True)
    max_score = _candidate_score(ranked[0], normalized_name, checked_year)
    top = [candidate for candidate in ranked if _candidate_score(candidate, normalized_name, checked_year) == max_score]
    result["candidates"] = [candidate.to_dict() for candidate in ranked[:max_candidates]]

    coordinate_candidates = [candidate for candidate in top if candidate.has_coordinate]
    if not coordinate_candidates:
        result["status"] = STATUS_NO_COORDINATE
        result["best_match"] = ranked[0].to_dict()
        result["note"] = "TGAZ 找到地名候选，但没有可用于现代边界反查的坐标"
        return result

    if len(coordinate_candidates) > 1:
        result["status"] = STATUS_AMBIGUOUS
        result["note"] = "TGAZ 返回多个同样可信的地名候选，需结合上下文选择"
        return result

    best = coordinate_candidates[0]
    result["status"] = STATUS_RESOLVED
    result["best_match"] = best.to_dict()
    resolver = boundary_resolver or ModernBoundaryResolver.from_cnmaps_data()
    assert best.longitude is not None and best.latitude is not None
    result["modern_administration"] = resolver.reverse_geocode(best.longitude, best.latitude)
    if result["modern_administration"]:
        result["note"] = "现代行政区划为 TGAZ 坐标落点/治所对应今地，不代表古代辖境"
    else:
        result["note"] = "TGAZ 坐标存在，但无法用当前现代边界库确认行政区划"
    return result


def validate_place_name(name: str) -> str:
    value = name.strip()
    if not value:
        raise PlaceResolverError("地名不能为空")
    if len(value) > MAX_PLACE_NAME_LENGTH:
        raise PlaceResolverError(f"地名长度不能超过 {MAX_PLACE_NAME_LENGTH} 字符")
    if not PLACE_NAME_PATTERN.fullmatch(value):
        raise PlaceResolverError("地名包含不允许的字符")
    return value


def validate_year(year: Optional[int]) -> Optional[int]:
    if year is None:
        return None
    if MIN_TGAZ_YEAR <= year <= MAX_TGAZ_YEAR:
        return year
    return None


def _load_cnmaps_records(data_root: Path) -> List[BoundaryRecord]:
    db_path = data_root / "index" / "administrative.db"
    records: List[BoundaryRecord] = []
    if db_path.exists():
        records = _load_cnmaps_records_from_db(data_root, db_path)
    if records:
        return records
    dataset_root = data_root / "datasets" / "administrative"
    if not dataset_root.exists():
        return []
    return [
        BoundaryRecord(name=path.stem, level="", path=path)
        for path in dataset_root.rglob("*.geojson")
    ] + [
        BoundaryRecord(name=path.stem, level="", path=path)
        for path in dataset_root.rglob("*.json")
    ]


def _load_cnmaps_records_from_db(data_root: Path, db_path: Path) -> List[BoundaryRecord]:
    records: List[BoundaryRecord] = []
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        tables = [row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        table = _select_administrative_table(con, tables)
        if not table:
            return []
        rows = con.execute(f'SELECT * FROM "{table}"').fetchall()
    except sqlite3.DatabaseError:
        return []
    finally:
        try:
            con.close()
        except UnboundLocalError:
            pass

    for row in rows:
        item = {key: row[key] for key in row.keys()}
        path = _resolve_geojson_path(data_root, _pick(item, "path", "geojson_path", "file", "filename"))
        name = _pick(item, "name", "fullname", "名称", "区/县", "district", "市", "city", "省/直辖市", "province")
        level = _pick(item, "level", "级别", "admin_level", "type")
        if not path and not name:
            continue
        adcode = str(_pick(item, "adcode", "code") or "")
        if not adcode and path:
            adcode = _adcode_from_path(path)
        records.append(
            BoundaryRecord(
                name=name or (path.stem if path else ""),
                level=str(level or ""),
                province=_pick(item, "province", "省/直辖市", "省", "prov") or "",
                city=_pick(item, "city", "市") or "",
                district=_pick(item, "district", "区/县", "县", "区") or "",
                adcode=adcode,
                source=_pick(item, "source", "来源") or "",
                path=path,
            )
        )
    return records


def _select_administrative_table(con: sqlite3.Connection, tables: Sequence[str]) -> Optional[str]:
    best_table: Optional[str] = None
    best_score = -1
    for table in tables:
        try:
            columns = [row[1].lower() for row in con.execute(f'PRAGMA table_info("{table}")')]
        except sqlite3.DatabaseError:
            continue
        score = 0
        for expected in ("path", "name", "level", "adcode", "province", "city", "district"):
            if expected in columns:
                score += 1
        if "administrative" in table.lower():
            score += 2
        if score > best_score:
            best_table = table
            best_score = score
    return best_table if best_score > 0 else None


def _resolve_geojson_path(data_root: Path, value: Any) -> Optional[Path]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    candidates = [
        Path(text),
        data_root / text,
        data_root / "datasets" / text,
        data_root / "datasets" / "administrative" / text,
    ]
    if not text.endswith((".json", ".geojson")):
        candidates.extend(path.with_suffix(".geojson") for path in list(candidates))
        candidates.extend(path.with_suffix(".json") for path in list(candidates))
    for path in candidates:
        if path.exists():
            return path
    return None


def _adcode_from_path(path: Path) -> str:
    match = re.search(r"(\d{6})", path.name)
    return match.group(1) if match else ""


def _records_from_response(data: Any) -> List[Mapping[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, Mapping)]
    if not isinstance(data, Mapping):
        return []
    for key in ("results", "Results", "result", "Result", "records", "items", "places", "placenames", "Placenames"):
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, Mapping)]
    if any(key in data for key in ("sys_id", "id", "uri", "spellings", "spatial", "feature_type")):
        return [data]
    return []


def _normalize_tgaz_record(record: Mapping[str, Any]) -> HistoricalPlace:
    spellings = record.get("spellings") or record.get("Spellings") or []
    names = _extract_names(spellings)
    for key in ("name", "placename", "label", "title"):
        value = record.get(key)
        if value:
            names.append(str(value).strip())
    names = _dedupe([name for name in names if name])
    feature = record.get("feature_type") or record.get("featureType") or record.get("type") or {}
    temporal = record.get("temporal") or record.get("Temporal") or {}
    spatial = record.get("spatial") or record.get("Spatial") or record
    context = record.get("historical_context") or record.get("historicalContext") or {}

    sys_id = _extract_tgaz_id(record)
    latitude = _parse_float(_pick(spatial, "latitude", "lat", "y", "Y"))
    longitude = _parse_float(_pick(spatial, "longitude", "lon", "lng", "x", "X"))

    return HistoricalPlace(
        sys_id=sys_id,
        primary_name=names[0] if names else "",
        names=names,
        feature_type=_feature_value(feature, "name") or str(feature or ""),
        feature_type_en=_feature_value(feature, "English") or _feature_value(feature, "english"),
        begin_year=_parse_int(_pick(temporal, "begin year", "begin_year", "begin", "from", "start")),
        end_year=_parse_int(_pick(temporal, "end year", "end_year", "end", "to", "stop")),
        longitude=longitude,
        latitude=latitude,
        parent=_extract_parent(context),
        present_location=_extract_present_location(spatial),
        data_source=str(record.get("data source") or record.get("data_source") or record.get("source") or ""),
        source_note=str(record.get("source note") or record.get("source_note") or record.get("note") or ""),
        raw=record,
    )


def _merge_place_records(base: HistoricalPlace, detail: HistoricalPlace) -> HistoricalPlace:
    return HistoricalPlace(
        sys_id=base.sys_id or detail.sys_id,
        primary_name=base.primary_name or detail.primary_name,
        names=_dedupe(base.names + detail.names),
        feature_type=base.feature_type or detail.feature_type,
        feature_type_en=base.feature_type_en or detail.feature_type_en,
        begin_year=base.begin_year if base.begin_year is not None else detail.begin_year,
        end_year=base.end_year if base.end_year is not None else detail.end_year,
        longitude=base.longitude if base.longitude is not None else detail.longitude,
        latitude=base.latitude if base.latitude is not None else detail.latitude,
        parent=base.parent or detail.parent,
        present_location=base.present_location or detail.present_location,
        data_source=base.data_source or detail.data_source,
        source_note=base.source_note or detail.source_note,
        raw=detail.raw or base.raw,
    )


def _candidate_score(candidate: HistoricalPlace, query: str, year: Optional[int]) -> int:
    score = 0
    if query in candidate.names:
        score += 100
    elif any(query in name or name in query for name in candidate.names):
        score += 40
    if candidate.is_active(year):
        score += 30
    if candidate.has_coordinate:
        score += 10
    if candidate.sys_id:
        score += 1
    return score


def _extract_tgaz_id(record: Mapping[str, Any]) -> str:
    for key in ("sys_id", "id", "identifier"):
        value = record.get(key)
        if value:
            match = TGAZ_ID_PATTERN.search(str(value))
            if match:
                return match.group(0)
    uri = str(record.get("uri") or record.get("@id") or "")
    match = TGAZ_ID_PATTERN.search(uri)
    return match.group(0) if match else ""


def _extract_names(spellings: Any) -> List[str]:
    names: List[str] = []
    if isinstance(spellings, list):
        for item in spellings:
            if isinstance(item, Mapping):
                for key in (
                    "written form",
                    "simplified Chinese",
                    "traditional Chinese",
                    "transcribed in Pinyin",
                    "name",
                    "label",
                    "value",
                ):
                    value = item.get(key)
                    if value:
                        names.append(str(value).strip())
            elif item:
                names.append(str(item).strip())
    return names


def _feature_value(feature: Any, key: str) -> str:
    if isinstance(feature, Mapping):
        return str(feature.get(key) or "").strip()
    return ""


def _extract_parent(context: Any) -> str:
    if not isinstance(context, Mapping):
        return ""
    parents = context.get("part of") or context.get("part_of") or context.get("parents") or []
    if not isinstance(parents, list):
        parents = [parents]
    values: List[str] = []
    for parent in parents:
        if isinstance(parent, Mapping):
            values.extend(str(parent.get(key) or "").strip() for key in ("name", "label", "placename"))
        elif parent:
            values.append(str(parent).strip())
    return " / ".join(_dedupe([value for value in values if value]))


def _extract_present_location(spatial: Any) -> str:
    if not isinstance(spatial, Mapping):
        return ""
    present = spatial.get("present_location") or spatial.get("present location") or []
    if not isinstance(present, list):
        present = [present]
    values: List[str] = []
    for item in present:
        if isinstance(item, Mapping):
            values.append(str(item.get("text") or item.get("name") or "").strip())
        elif item:
            values.append(str(item).strip())
    return " / ".join(_dedupe([value for value in values if value]))


def _pick(mapping: Mapping[str, Any], *keys: str) -> Any:
    if not isinstance(mapping, Mapping):
        return None
    lowered = {str(key).lower(): value for key, value in mapping.items()}
    for key in keys:
        if key in mapping:
            value = mapping[key]
            if value is not None and str(value) != "":
                return value
        if key.lower() in lowered:
            value = lowered[key.lower()]
            if value is not None and str(value) != "":
                return value
    return None


def _parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    match = re.search(r"-?\d+", str(value))
    return int(match.group(0)) if match else None


def _parse_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _dedupe(values: Iterable[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _select_geojson_geometry(data: Mapping[str, Any], adcode: str, name: str) -> Optional[Mapping[str, Any]]:
    if data.get("type") == "Feature":
        return data.get("geometry") if isinstance(data.get("geometry"), Mapping) else None
    if data.get("type") in {"Polygon", "MultiPolygon", "GeometryCollection"}:
        return data
    if data.get("type") == "FeatureCollection":
        features = [feature for feature in data.get("features") or [] if isinstance(feature, Mapping)]
        if not features:
            return None
        for feature in features:
            props = feature.get("properties") if isinstance(feature.get("properties"), Mapping) else {}
            if adcode and str(_pick(props, "adcode", "code", "id")) == adcode:
                return feature.get("geometry") if isinstance(feature.get("geometry"), Mapping) else None
            if name and name in {
                str(_pick(props, "name") or ""),
                str(_pick(props, "fullname") or ""),
            }:
                return feature.get("geometry") if isinstance(feature.get("geometry"), Mapping) else None
        if len(features) == 1:
            geometry = features[0].get("geometry")
            return geometry if isinstance(geometry, Mapping) else None
    return None


def _point_in_geometry(longitude: float, latitude: float, geometry: Mapping[str, Any]) -> bool:
    geom_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geom_type == "Polygon" and isinstance(coordinates, list):
        return _point_in_polygon(longitude, latitude, coordinates)
    if geom_type == "MultiPolygon" and isinstance(coordinates, list):
        return any(_point_in_polygon(longitude, latitude, polygon) for polygon in coordinates)
    if geom_type == "GeometryCollection":
        geometries = geometry.get("geometries") or []
        return any(isinstance(item, Mapping) and _point_in_geometry(longitude, latitude, item) for item in geometries)
    return False


def _point_in_polygon(longitude: float, latitude: float, polygon: Sequence[Any]) -> bool:
    if not polygon:
        return False
    outer = polygon[0]
    if not _point_in_ring(longitude, latitude, outer):
        return False
    for hole in polygon[1:]:
        if _point_in_ring(longitude, latitude, hole):
            return False
    return True


def _point_in_ring(longitude: float, latitude: float, ring: Sequence[Any]) -> bool:
    inside = False
    points = [_xy(point) for point in ring if _xy(point) is not None]
    if len(points) < 3:
        return False
    previous_x, previous_y = points[-1]
    for current_x, current_y in points:
        if _point_on_segment(longitude, latitude, previous_x, previous_y, current_x, current_y):
            return True
        if (current_y > latitude) != (previous_y > latitude):
            x_intersection = (previous_x - current_x) * (latitude - current_y) / (previous_y - current_y) + current_x
            if longitude < x_intersection:
                inside = not inside
        previous_x, previous_y = current_x, current_y
    return inside


def _point_on_segment(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> bool:
    epsilon = 1e-10
    cross = (px - x1) * (y2 - y1) - (py - y1) * (x2 - x1)
    if abs(cross) > epsilon:
        return False
    return min(x1, x2) - epsilon <= px <= max(x1, x2) + epsilon and min(y1, y2) - epsilon <= py <= max(y1, y2) + epsilon


def _geometry_bbox(geometry: Mapping[str, Any]) -> Optional[Tuple[float, float, float, float]]:
    points = list(_iter_points(geometry.get("coordinates")))
    if not points and geometry.get("type") == "GeometryCollection":
        for item in geometry.get("geometries") or []:
            if isinstance(item, Mapping):
                points.extend(_iter_points(item.get("coordinates")))
    if not points:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _iter_points(value: Any) -> Iterable[Tuple[float, float]]:
    if not isinstance(value, list):
        return
    if value and isinstance(value[0], (int, float)) and len(value) >= 2:
        yield float(value[0]), float(value[1])
        return
    for item in value:
        yield from _iter_points(item)


def _xy(point: Any) -> Optional[Tuple[float, float]]:
    if isinstance(point, (list, tuple)) and len(point) >= 2:
        try:
            return float(point[0]), float(point[1])
        except (TypeError, ValueError):
            return None
    return None


def _point_in_bbox(longitude: float, latitude: float, bbox: Tuple[float, float, float, float]) -> bool:
    min_x, min_y, max_x, max_y = bbox
    return min_x <= longitude <= max_x and min_y <= latitude <= max_y


def _name_for_rank(records: Sequence[BoundaryRecord], rank: int) -> str:
    for record in records:
        if record.rank() == rank:
            return record.name
    return ""


def _print_human(result: Mapping[str, Any]) -> None:
    query = result.get("query") or {}
    print(f"查询地名：{query.get('name')}")
    if query.get("year") is not None:
        print(f"限定年份：{query.get('year')}")
    print(f"状态：{result.get('status')}")

    best = result.get("best_match") or {}
    if best:
        print("\nTGAZ 候选：")
        span = _format_span(best.get("begin_year"), best.get("end_year"))
        coord = _format_coord(best.get("longitude"), best.get("latitude"))
        print(f"- {best.get('name') or best.get('id')} {best.get('feature_type') or ''} {span} {coord}".strip())

    admin = result.get("modern_administration")
    if admin:
        parts = [admin.get("province"), admin.get("city"), admin.get("district")]
        print("\n今地：")
        print(" / ".join(part for part in parts if part))
        if admin.get("adcode"):
            print(f"行政区划代码：{admin['adcode']}")
    elif result.get("status") == STATUS_AMBIGUOUS:
        print("\n候选：")
        for item in result.get("candidates") or []:
            span = _format_span(item.get("begin_year"), item.get("end_year"))
            coord = _format_coord(item.get("longitude"), item.get("latitude"))
            print(f"- {item.get('name') or item.get('id')} {item.get('feature_type') or ''} {span} {coord}".strip())

    if result.get("note"):
        print(f"\n说明：{result['note']}")


def _format_span(begin: Any, end: Any) -> str:
    if begin is None and end is None:
        return ""
    return f"({begin if begin is not None else '?'}-{end if end is not None else '?'})"


def _format_coord(longitude: Any, latitude: Any) -> str:
    if longitude is None or latitude is None:
        return ""
    return f"[{longitude}, {latitude}]"


def main() -> int:
    parser = argparse.ArgumentParser(description="Resolve a historical Chinese placename to a present administrative unit.")
    parser.add_argument("name", help='Historical placename, e.g. "顺天府".')
    parser.add_argument("--year", type=int, help="Historical year between -222 and 1911.")
    parser.add_argument("--feature-type", help="Optional TGAZ feature type filter, e.g. xian, fu, 州.")
    parser.add_argument("--json", action="store_true", help="Print structured JSON.")
    args = parser.parse_args()

    try:
        result = resolve_place(args.name, year=args.year, feature_type=args.feature_type)
    except PlaceResolverError as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, ensure_ascii=False, indent=2))
        else:
            print(f"查询失败: {exc}")
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
