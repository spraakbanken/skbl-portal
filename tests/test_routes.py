import pytest


@pytest.mark.parametrize("route", ["/sv", "/en"])
def test_routes(client, route: str, snapshot):
    response = client.get(route)

    assert response.data == snapshot
