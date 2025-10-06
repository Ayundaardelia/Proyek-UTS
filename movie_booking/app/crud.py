from typing import List, Dict, Tuple
from fastapi import HTTPException
from .schemas import (
    MovieCreate, MovieUpdate, Movie,
    ShowtimeCreate, Showtime, SeatStatus,
    SeatCell, SeatLayout
)
from . import storage
from .utils import apply_promo, code_from_row_col, seat_type_for
import uuid
from datetime import datetime


# =========================
#        MOVIES
# =========================
def create_movie(data: MovieCreate) -> Movie:
    """Buat movie baru dan simpan ke storage (in-memory)."""
    m = Movie(id=storage.next_movie_id(), **data.model_dump())
    return storage.save_movie(m)

def update_movie(movie_id: int, data: MovieUpdate) -> Movie:
    """Update field yang diberikan (partial update) untuk movie tertentu."""
    m = storage.get_movie(movie_id)
    if not m:
        raise HTTPException(404, "Movie not found")
    updated = m.model_copy(update=data.model_dump(exclude_unset=True))
    return storage.save_movie(updated)

def delete_movie(movie_id: int) -> None:
    """Hapus movie. Sekaligus cascade hapus showtime & seat map miliknya."""
    if not storage.delete_movie(movie_id):
        raise HTTPException(404, "Movie not found")


# =========================
#       SHOWTIMES
# =========================
def create_showtime(movie_id: int, data: ShowtimeCreate) -> Showtime:
    """Buat showtime baru untuk movie tertentu + inisialisasi seat map & metadata layout."""
    if not storage.get_movie(movie_id):
        raise HTTPException(404, "Movie not found")
    st = Showtime(id=storage.next_showtime_id(), movie_id=movie_id, **data.model_dump())
    return storage.save_showtime(st)


# =========================
#    SEATS / LAYOUT
# =========================
def get_seats_status(showtime_id: int) -> Dict[str, SeatStatus]:
    """Kembalikan peta kursi: { 'A1': 'available', ... }."""
    seat_map = storage.seats_map(showtime_id)
    if seat_map is None:
        raise HTTPException(404, "Showtime not found")
    return seat_map

def get_seat_layout(showtime_id: int) -> SeatLayout:
    """
    Kembalikan layout 2D untuk visualisasi:
    - screen_side, aisles_cols
    - grid[row][col] -> SeatCell(code, status, seat_type)
    """
    st = storage.get_showtime(showtime_id)
    seat_map = storage.seats_map(showtime_id)
    meta = storage.showtime_meta(showtime_id)
    if not st or seat_map is None or meta is None:
        raise HTTPException(404, "Showtime not found")

    vip = meta["vip"]
    disabled = meta["disabled"]
    grid: List[List[SeatCell]] = []

    for r in range(1, st.rows + 1):
        row_cells: List[SeatCell] = []
        for c in range(1, st.cols + 1):
            code = code_from_row_col(r, c)
            status = seat_map.get(code)
            if status is None:
                continue
            s_type = seat_type_for(code, vip, disabled)
            row_cells.append(SeatCell(row=r, col=c, code=code, status=status, seat_type=s_type))
        grid.append(row_cells)

    return SeatLayout(
        showtime_id=st.id,
        rows=st.rows,
        cols=st.cols,
        screen_side=st.screen_side,
        aisles_cols=meta["aisles"],
        legend={
            "available": "Kursi dapat dipesan",
            "reserved": "Sedang di-cart pengguna lain",
            "booked":   "Sudah dibayar",
            "blocked":  "Dinonaktifkan",
            "vip":      "Kursi VIP",
            "standard": "Kursi standar",
            "screen_side": "Posisi layar relatif grid",
            "aisles_cols":  "Nomor kolom lorong/aisle (1-based)"
        },
        grid=grid
    )


# =========================
#          CART
# =========================
def add_to_cart(user_id: str, showtime_id: int, seats: List[str]) -> tuple[str, float]:
    """
    Reserve kursi (status -> reserved) dan masukkan ke cart user.
    Return: (cart_item_id, subtotal)
    """
    seat_map = storage.seats_map(showtime_id)
    st = storage.get_showtime(showtime_id)
    meta = storage.showtime_meta(showtime_id)
    if seat_map is None or st is None or meta is None:
        raise HTTPException(404, "Showtime not found")

    # validasi kursi exist & available
    for s in seats:
        if s not in seat_map:
            raise HTTPException(400, f"Seat {s} does not exist")
        if seat_map[s] != SeatStatus.available:
            raise HTTPException(400, f"Seat {s} is not available")

    # reserve
    for s in seats:
        seat_map[s] = SeatStatus.reserved

    cart_item_id = str(uuid.uuid4())[:8]
    items = storage.get_cart(user_id) or []
    items.append((cart_item_id, showtime_id, list(seats)))
    storage.set_cart(user_id, items)
    subtotal = st.price * len(seats)
    return cart_item_id, subtotal

def remove_from_cart(user_id: str, cart_item_id: str | None, seats: List[str] | None) -> None:
    """
    Hapus kursi tertentu dari item (partial) atau hapus item penuh berdasarkan cart_item_id.
    Mengembalikan kursi yang dilepas ke status 'available'.
    """
    items = storage.get_cart(user_id) or []
    new_items: List[Tuple[str, int, List[str]]] = []
    changed = False

    for cid, stid, seat_list in items:
        seat_map = storage.seats_map(stid)

        # hapus seluruh item
        if cart_item_id and cid == cart_item_id:
            for s in seat_list:
                seat_map[s] = SeatStatus.available
            changed = True
            continue

        # hapus sebagian kursi dari item mana pun
        if seats:
            keep = [s for s in seat_list if s not in seats]
            if len(keep) != len(seat_list):
                for s in seat_list:
                    if s in seats:
                        seat_map[s] = SeatStatus.available
                changed = True
                if keep:
                    new_items.append((cid, stid, keep))
                continue

        new_items.append((cid, stid, seat_list))

    if not changed and len(new_items) == len(items):
        raise HTTPException(400, "No matching cart item or seats to remove")

    storage.set_cart(user_id, new_items)

def get_cart_summary(user_id: str) -> tuple[list, float]:
    """Hitung ulang subtotal per item & total cart untuk user."""
    items = storage.get_cart(user_id) or []
    enriched = []
    total = 0.0
    for cid, stid, seat_list in items:
        st = storage.get_showtime(stid)
        subtotal = st.price * len(seat_list)
        total += subtotal
        enriched.append({"id": cid, "showtime_id": stid, "seats": seat_list, "subtotal": subtotal})
    return enriched, total


# =========================
#         CHECKOUT
# =========================
def checkout(user_id: str, promo_code: str | None) -> dict:
    """
    Validasi kursi masih reserved, hitung total & promo, finalisasi -> booked,
    kosongkan cart, generate booking_code, SIMPAN booking agar bisa dicek lagi.
    """
    items = storage.get_cart(user_id) or []
    if not items:
        raise HTTPException(400, "Cart is empty")

    total = 0.0
    result_items = []
    for cid, stid, seat_list in items:
        st = storage.get_showtime(stid)
        seat_map = storage.seats_map(stid)
        for s in seat_list:
            if seat_map.get(s) != SeatStatus.reserved:
                raise HTTPException(400, f"Seat {s} not reserved anymore")
        subtotal = st.price * len(seat_list)
        total += subtotal
        result_items.append({"id": cid, "showtime_id": stid, "seats": seat_list, "subtotal": subtotal})

    discount = apply_promo(total, promo_code)
    total_paid = max(0.0, total - discount)

    # finalize -> booked
    for _, stid, seat_list in items:
        seat_map = storage.seats_map(stid)
        for s in seat_list:
            seat_map[s] = SeatStatus.booked

    storage.set_cart(user_id, [])
    code = f"BKG-{uuid.uuid4().hex[:10].upper()}"
    timestamp = datetime.now().isoformat(timespec="seconds")

    payload = {
        "booking_code": code,
        "user_id": user_id,
        "total_before_discount": total,
        "discount_amount": discount,
        "total_paid": total_paid,
        "items": result_items,
        "timestamp": timestamp
    }

    # SIMPAN booking agar bisa dicek ulang
    storage.save_booking(payload)
    return payload


# =========================
#       TICKETS (NEW)
# =========================
def get_booking(booking_code: str) -> dict:
    """Ambil tiket berdasarkan booking_code (untuk /tickets/{booking_code})."""
    b = storage.get_booking(booking_code)
    if not b:
        raise HTTPException(404, "Ticket not found")
    return b

def list_user_bookings(user_id: str) -> list[dict]:
    """List semua tiket milik user (untuk /users/{user_id}/tickets)."""
    return storage.list_bookings_by_user(user_id)
