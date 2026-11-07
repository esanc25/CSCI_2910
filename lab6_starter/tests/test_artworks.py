def test_get_seeded_artwork(client, seeded_db):
    # Arrange: seeded_db has already loaded the 11 artworks (the Mona Lisa is first)
    expected = {"id": 1, **seeded_db[0]}

    # Act
    response = client.get("/artworks/1")

    # Assert
    assert response.status_code == 200
    assert response.json() == expected

def test_list_artworks_empty(client):
    #no seed data(?)

    response = client.get("/artworks/")

    assert response.status_code == 200
    assert response.json() == []

def test_create_artwork (client, sample_artwork): 
    response = client.post("/artworks/", json=sample_artwork)
    assert response.status_code == 201
    data = response.json()

    assert isinstance(data["id"], int)
    for key, value in sample_artwork.items():
        assert data[key] == value

def test_create_artwork_is_saved(client, created_artwork):

    artwork_id = created_artwork["id"]

    response = client.get(f"/artworks/{artwork_id}")

    assert response.status_code == 200
    assert response.json() == created_artwork

def test_update_artwork(client, created_artwork, updated_artwork):
    artwork_id = created_artwork["id"]

    response = client.put(
        f"/artworks/{artwork_id}",
        json=updated_artwork
    )

    assert response.status_code == 200
    data = response.json()

    assert data["id"] == artwork_id

    for key, value in updated_artwork.items():
        assert data[key] == value

    get_response = client.get(f"/artworks/{artwork_id}")

    assert get_response.status_code == 200
    assert get_response.json() == data

def test_delete_artwork(client, created_artwork):
    artwork_id = created_artwork["id"]

    response = client.delete(f"/artworks/{artwork_id}")

    assert response.status_code == 204
    assert response.content == b""

    get_response = client.get(f"/artworks/{artwork_id}")

    assert get_response.status_code == 404


###PART 5 unhappy 

import pytest


@pytest.mark.parametrize(
    "method, use_body",
    [
        ("get", False),
        ("put", True),
        ("delete", False),
    ],
    ids=["get", "put", "delete"],
)
def test_artwork_not_found(client, sample_artwork, method, use_body):
    kwargs = {"json": sample_artwork} if use_body else {}
    response = client.request(method, "/artworks/9999", **kwargs)
    assert response.status_code == 404
    assert response.json() == {"detail": "Artwork not found"}

def test_non_integer_id(client): 
    response = client.get("/artworks/mona-lisa")
    assert response.status_code ==422

def test_create_duplicate (client, created_artwork, sample_artwork):
    response = client.post("/artworks/", json=sample_artwork)

    assert response.status_code == 409
    assert response.json() == {"detail" : "An artwork with that title and artist already exists"}

def test_create_duplicate_ignores_case (client, created_artwork, sample_artwork): 
    duplicate_artwork = sample_artwork.copy()
    duplicate_artwork["title"] = duplicate_artwork["title"].upper()
    duplicate_artwork["artist"] = duplicate_artwork["artist"].lower()

    response = client.post("/artworks/", json=duplicate_artwork)

    assert response.status_code == 409
    assert response.json() == {
        "detail": "An artwork with that title and artist already exists"
    }

def test_update_into_duplicate(client, seeded_db):
    duplicate_artwork = seeded_db[0].copy()
    artwork_id = 2

    response = client.put(
        f"/artworks/{artwork_id}",
        json=duplicate_artwork
    )

    assert response.status_code == 409
    assert response.json() == {
        "detail": "An artwork with that title and artist already exists"
    }

    get_response = client.get(f"/artworks/{artwork_id}")

    assert get_response.status_code == 200
    assert get_response.json()["title"] == "Lady with an Ermine"

def test_update_same_title_and_artist_is_allowed(
    client, created_artwork
):
    updated_data = created_artwork.copy()

    updated_data["museum"] = "The Metropolitan Museum of Art"

    artwork_id = created_artwork["id"]

    response = client.put(
        f"/artworks/{artwork_id}",
        json=updated_data
    )

    assert response.status_code == 200
    assert response.json()["title"] == created_artwork["title"]
    assert response.json()["artist"] == created_artwork["artist"]
    assert response.json()["museum"] == "The Metropolitan Museum of Art"


@pytest.mark.parametrize(
    "missing_field",
    ["title", "artist", "year", "medium", "museum", "image_url"],
    ids=["title", "artist", "year", "medium", "museum", "image_url"],
)
def test_create_missing_field(client, sample_artwork, missing_field):
    artwork = sample_artwork.copy()
    artwork.pop(missing_field)

    response = client.post("/artworks/", json=artwork)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", missing_field]


@pytest.mark.parametrize(
    "field, bad_value",
    [
        ("year", 3000),
        ("year", "nineteen-oh-seven"),
        ("title", ""),
    ],
    ids=["future-year", "year-not-int", "empty-title"],
)
def test_create_invalid_value(client, sample_artwork, field, bad_value):
    artwork = sample_artwork.copy()
    artwork[field] = bad_value

    response = client.post("/artworks/", json=artwork)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "params, expected_count",
    [
        ({"limit": 3}, 3),
        ({"skip": 3, "limit": 4}, 4),
        ({"skip": 10, "limit": 5}, 1),
        ({"limit": 0}, 0),
        ({"skip": 20, "limit": 3}, 0),
    ],
    ids=["first-three", "skip-three", "last-artwork", "zero-limit", "past-end"],
)
def test_pagination_counts(client, seeded_db, params, expected_count):
    response = client.get("/artworks/", params=params)

    assert response.status_code == 200
    assert len(response.json()) == expected_count


@pytest.mark.parametrize(
    "params",
    [
        ({"skip": -1}),
        ({"limit": 101}),
    ],
    ids=["negative-skip", "limit-too-large"],
)
def test_pagination_invalid(client, params):
    response = client.get("/artworks/", params=params)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "artist",
    ["Claude Monet", "monet", "Nobody"],
    ids=["full-name", "partial-lowercase", "no-results"],
)
def test_filter_by_artist(client, seeded_db, artist):
    expected_titles = [
        artwork["title"]
        for artwork in seeded_db
        if artist.lower() in artwork["artist"].lower()
    ]

    response = client.get("/artworks/", params={"artist": artist})

    assert response.status_code == 200

    actual_titles = [
        artwork["title"]
        for artwork in response.json()
    ]

    assert actual_titles == expected_titles