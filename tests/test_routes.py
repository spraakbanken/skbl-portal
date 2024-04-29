import pytest


@pytest.mark.parametrize("route", ["/sv", "/en", "/sv/om-skbl", "/en/about-skbl"])
def test_routes(client, route: str, snapshot):
    response = client.get(route)

    assert response.data == snapshot
