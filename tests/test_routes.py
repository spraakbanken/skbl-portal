import pytest


@pytest.mark.parametrize("route", ["/sv", "/en", "/sv/om-skbl", "/en/about-skbl"])
def test_routes(client, route: str, snapshot):
    response = client.get(route)

    assert response.status_code == 200  # noqa: PLR2004
    response_text = response.get_data(as_text=True)
    assert response_text[:100] == snapshot
