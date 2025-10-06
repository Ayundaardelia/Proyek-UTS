from typing import List, Optional, Dict
from pydantic import BaseModel, Field, validator
from enum import Enum

# ---------- ENUM ----------
class SeatStatus(str, Enum):
    available = "available"
    reserved  = "reserved"
    booked    = "booked"
    blocked   = "blocked"   # kursi dinonaktifkan (tidak dipakai)

class ScreenSide(str, Enum):
    top = "top"       # layar di sisi atas (umum: baris A dekat layar)
    bottom = "bottom"
    left = "left"
    right = "right"

# ---------- MOVIE ----------
class MovieBase(BaseModel):
    title: str = Field(..., example="Interstellar")
    synopsis: Optional[str] = Field(None, example="A journey through space and time.")
    duration_min: int = Field(..., ge=1, example=169)
    rating: Optional[str] = Field(None, example="PG-13")
    genre: Optional[str] = Field(None, example="Sci-Fi")

class MovieCreate(MovieBase):
    pass

class MovieUpdate(BaseModel):
    title: Optional[str] = None
    synopsis: Optional[str] = None
    duration_min: Optional[int] = Field(None, ge=1)
    rating: Optional[str] = None
    genre: Optional[str] = None

class Movie(MovieBase):
    id: int

# ---------- SHOWTIME ----------
class ShowtimeBase(BaseModel):
    day: str = Field(..., example="2025-10-15")
    time: str = Field(..., example="19:00")  # HH:MM (24 jam)
    studio: str = Field(..., example="Studio 1")
    price: float = Field(..., ge=0.0, example=50000.0)
    rows: int = Field(..., ge=1, le=26, example=6)
    cols: int = Field(..., ge=1, le=20, example=10)

    # ---- metadata layout opsional ----
    screen_side: ScreenSide = ScreenSide.top
    aisles_cols: Optional[List[int]] = Field(
        default=None, example=[5],
        description="Nomor kolom yang menjadi lorong/aisle (1-based)."
    )
    vip_seats: Optional[List[str]] = Field(
        default=None, example=["A1","A2","B1","B2"],
        description="Kode kursi VIP."
    )
    disabled_seats: Optional[List[str]] = Field(
        default=None, example=["A10","B10"],
        description="Kursi dinonaktifkan (blocked)."
    )

    @validator("day")
    def _day(cls, v):
        if len(v.split("-")) != 3:
            raise ValueError("day must be YYYY-MM-DD")
        return v

    @validator("time")
    def _time(cls, v):
        if len(v.split(":")) != 2:
            raise ValueError("time must be HH:MM 24h")
        return v

class ShowtimeCreate(ShowtimeBase):
    pass

class Showtime(ShowtimeBase):
    id: int
    movie_id: int

# ---------- CART & CHECKOUT ----------
class AddToCartRequest(BaseModel):
    user_id: str
    showtime_id: int
    seats: List[str]

class RemoveFromCartRequest(BaseModel):
    user_id: str
    cart_item_id: Optional[str] = None
    seats: Optional[List[str]] = None

class CartItem(BaseModel):
    id: str
    showtime_id: int
    seats: List[str]
    subtotal: float

class Cart(BaseModel):
    user_id: str
    items: List[CartItem]
    total: float

class CheckoutRequest(BaseModel):
    user_id: str
    promo_code: Optional[str] = None

class CheckoutResponse(BaseModel):
    booking_code: str
    user_id: str
    total_before_discount: float
    discount_amount: float
    total_paid: float
    items: List[CartItem]
    timestamp: str

# ---------- LAYOUT VISUAL ----------
class SeatCell(BaseModel):
    row: int
    col: int
    code: str
    status: SeatStatus
    seat_type: str  # "standard" | "vip" | "blocked"

class SeatLayout(BaseModel):
    showtime_id: int
    rows: int
    cols: int
    screen_side: ScreenSide
    aisles_cols: List[int]
    legend: Dict[str, str]
    grid: List[List[SeatCell]]
