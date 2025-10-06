import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_full_booking_flow_with_layout():
    # 1) create movie
    movie = client.post("/admin/movies", json={
        "title": "Interstellar",
        "synopsis": "Space and time",
        "duration_min": 169,
        "rating": "PG-13",
        "genre": "Sci-Fi"
    }).json()
    movie_id = movie["id"]

    # 2) create showtime (dengan metadata layout)
    st = client.post(f"/admin/movies/{movie_id}/showtimes", json={
        "day": "2025-10-15",
        "time": "19:00",
        "studio": "Studio 1",
        "price": 50000,
        "rows": 2,
        "cols": 4,
        "screen_side": "top",
        "aisles_cols": [3],
        "vip_seats": ["A1", "A2"],
        "disabled_seats": ["B4"]
    }).json()
    st_id = st["id"]

    # 3) get layout (untuk UI)
    layout = client.get(f"/showtimes/{st_id}/layout").json()
    assert layout["rows"] == 2 and layout["cols"] == 4
    assert layout["screen_side"] == "top"
    # A1 harus VIP, B4 blocked
    grid = layout["grid"]
    assert grid[0][0]["code"] == "A1" and grid[0][0]["seat_type"] == "vip"
    assert grid[1][3]["code"] == "B4" and grid[1][3]["seat_type"] == "blocked"

    # 4) add to cart (reserve A1, A2)
    item = client.post("/cart/add", json={
        "user_id": "alice",
        "showtime_id": st_id,
        "seats": ["A1","A2"]
    }).json()
    assert item["subtotal"] == 2 * 50000

    # 5) get seats -> status reserved
    seats = client.get(f"/showtimes/{st_id}/seats").json()
    assert seats["A1"] == "reserved" and seats["A2"] == "reserved"

    # 6) checkout (pakai promo)
    data = client.post("/checkout", json={
        "user_id": "alice", "promo_code": "DISCOUNT10"
    }).json()
    assert data["total_before_discount"] == 100000
    assert round(data["discount_amount"]) == round(0.1 * 100000)
    assert data["total_paid"] == pytest.approx(90000)

    # 7) seats now booked
    seats2 = client.get(f"/showtimes/{st_id}/seats").json()
    assert seats2["A1"] == "booked" and seats2["A2"] == "booked"

def test_remove_partial_and_whole_item():
    # movie + showtime
    mv = client.post("/admin/movies", json={"title": "Dune", "synopsis": "Spice", "duration_min": 155}).json()
    st = client.post(f"/admin/movies/{mv['id']}/showtimes", json={
        "day": "2025-10-20", "time": "20:00", "studio": "S2", "price": 40000, "rows": 1, "cols": 4
    }).json()
    st_id = st["id"]

    # add 3 seats
    item = client.post("/cart/add", json={"user_id": "bob", "showtime_id": st_id, "seats": ["A1","A2","A3"]}).json()

    # remove only A2
    r = client.delete("/cart/remove", json={"user_id": "bob", "seats": ["A2"]})
    assert r.status_code == 200
    cart = client.get("/cart/bob").json()
    assert cart["items"][0]["seats"] == ["A1","A3"]

    # remove by item id
    r = client.delete("/cart/remove", json={"user_id": "bob", "cart_item_id": item["id"]})
    assert r.status_code == 200
    cart = client.get("/cart/bob").json()
    assert cart["total"] == 0 and cart["items"] == []
