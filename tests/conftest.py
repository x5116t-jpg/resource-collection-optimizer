import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import networkx as nx
import pytest

from src.services.distance_matrix import build_distance_matrix
from src.services.vehicle_catalog import VehicleType


@pytest.fixture
def simple_graph() -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_edge("depot", "pickup1", length=100)
    graph.add_edge("pickup1", "sink", length=150)
    graph.add_edge("sink", "depot", length=200)
    graph.add_edge("depot", "sink", length=500)
    graph.add_edge("depot", "pickup2", length=120)
    graph.add_edge("pickup2", "sink", length=130)
    return graph


@pytest.fixture
def simple_graph_dm(simple_graph):
    points = [
        {"id": "depot", "osmid": "depot"},
        {"id": "pickup1", "osmid": "pickup1"},
        {"id": "pickup2", "osmid": "pickup2"},
        {"id": "sink", "osmid": "sink"},
    ]
    return build_distance_matrix(simple_graph, points)


@pytest.fixture
def vehicle_small() -> VehicleType:
    return VehicleType(name="small", capacity_kg=300, fixed_cost=1000, per_km_cost=50)


@pytest.fixture
def vehicle_large() -> VehicleType:
    return VehicleType(name="large", capacity_kg=1000, fixed_cost=1500, per_km_cost=40)
