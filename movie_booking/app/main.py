# app/main.py
from fastapi import FastAPI, HTTPException
from typing import List, Dict

from .schemas import (
    # Movie / Showtime
    MovieCreate, MovieUpdate, Movie,
    ShowtimeCreate, Showtime, SeatStatus,
    # Cart & Checkout
    AddToCartRequest, RemoveFromCartRequest, Cart, CartItem,
    CheckoutRequest, CheckoutResponse,
    # Visual Layout
    SeatLayout,
)
from . import crud, storage


app = FastAPI(
    title="Movie Booking System (Project 5)",
    description=(
        "Backend tanpa DB/JWT (in-memory). "
        "Fitur: kelola film & showtime, layout kursi visual, cart, checkout, dan cek tiket."
    ),
    version="1.0.0",
)

# =========================
#         ADMIN
# =========================

@app.post("/admin/movies", response_model=Movie, tags=["Admin"])
def create_movie(movie: MovieCreate):
    return crud.create_movie(movie)

@app.get("/admin/movies", response_model=List[Movie], tags=["Admin"])
def list_movies_admin():
    return storage.list_movies()

@app.get("/admin/movies/{movie_id}", response_model=Movie, tags=["Admin"])
def get_movie_admin(movie_id: int):
    m = storage.get_movie(movie_id)
    if not m:
        raise HTTPException(404, "Movie not found")
    return m

@app.put("/admin/movies/{movie_id}", response_model=Movie, tags=["Admin"])
def update_movie_admin(movie_id: int, data: MovieUpdate):
    return crud.update_movie(movie_id, data)

@app.delete("/admin/movies/{movie_id}", tags=["Admin"])
def delete_movie_admin(movie_id: int):
    crud.delete_movie(movie_id)
    return {"message": "Movie deleted"}

@app.post("/admin/movies/{movie_id}/showtimes", response_model=Showtime, tags=["Admin"])
def create_showtime_admin(movie_id: int, data: ShowtimeCreate):
    return crud.create_showtime(movie_id, data)

@app.get("/admin/showtimes", response_model=List[Showtime], tags=["Admin"])
def list_showtimes_admin():
    return storage.list_showtimes()


# =========================
#          USER
# =========================

@app.get("/movies", response_model=List[Movie], tags=["User"])
def list_movies_user():
    return storage.list_movies()

@app.get("/movies/{movie_id}/showtimes", response_model=List[Showtime], tags=["User"])
def list_showtimes_for_movie(movie_id: int):
    return storage.list_showtimes(movie_id)

@app.get("/showtimes/{showtime_id}/seats", response_model=Dict[str, SeatStatus], tags=["User"])
def get_seats(showtime_id: int):
    return crud.get_seats_status(showtime_id)

# Layout kursi 2D + metadata (screen_side, aisles_cols) untuk front-end
@app.get("/showtimes/{showtime_id}/layout", response_model=SeatLayout, tags=["User"])
def get_layout(showtime_id: int):
    return crud.get_seat_layout(showtime_id)

# -------- Cart & Checkout --------
@app.post("/cart/add", response_model=CartItem, tags=["User"])
def add_to_cart(req: AddToCartRequest):
    cid, subtotal = crud.add_to_cart(req.user_id, req.showtime_id, req.seats)
    return {"id": cid, "showtime_id": req.showtime_id, "seats": req.seats, "subtotal": subtotal}

@app.get("/cart/{user_id}", response_model=Cart, tags=["User"])
def get_cart(user_id: str):
    items, total = crud.get_cart_summary(user_id)
    return {"user_id": user_id, "items": items, "total": total}

@app.delete("/cart/remove", tags=["User"])
def remove_from_cart(req: RemoveFromCartRequest):
    crud.remove_from_cart(req.user_id, req.cart_item_id, req.seats)
    return {"message": "Updated cart"}

@app.post("/checkout", response_model=CheckoutResponse, tags=["User"])
def checkout(req: CheckoutRequest):
    return crud.checkout(req.user_id, req.promo_code)


# =========================
#        TICKETS (NEW)
# =========================

# Lihat detail tiket berdasarkan booking_code
@app.get("/tickets/{booking_code}", response_model=CheckoutResponse, tags=["User"])
def get_ticket(booking_code: str):
    return crud.get_booking(booking_code)

# List semua tiket milik user
@app.get("/users/{user_id}/tickets", response_model=List[CheckoutResponse], tags=["User"])
def list_tickets(user_id: str):
    return crud.list_user_bookings(user_id)
