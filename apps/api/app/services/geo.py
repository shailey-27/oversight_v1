"""
Haversine geo-fence service.
Replaces PostGIS — pure Python, works with Neon DB (plain lat/lng columns).
"""

import math


EARTH_RADIUS_M = 6_371_000  # meters


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Returns the great-circle distance in meters between two GPS coordinates.
    Uses the Haversine formula — accurate to within ~0.3% for typical distances.
    """
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return EARTH_RADIUS_M * c


def check_geo_fence(
    check_lat: float,
    check_lng: float,
    center_lat: float,
    center_lng: float,
    radius_meters: int,
) -> dict:
    """
    Validates whether a GPS coordinate is within the institution's geo-fence.

    Returns:
        {
            "within_fence": bool,
            "distance_meters": float,
            "status": "valid" | "outside_fence" | "suspicious"
        }
    """
    distance = haversine_distance(check_lat, check_lng, center_lat, center_lng)

    if distance <= radius_meters:
        status = "valid"
        within = True
    elif distance <= radius_meters * 2:
        # Within 2x the fence — could be GPS drift, flag but allow
        status = "suspicious"
        within = False
    else:
        status = "outside_fence"
        within = False

    return {
        "within_fence": within,
        "distance_meters": round(distance, 1),
        "status": status,
    }
