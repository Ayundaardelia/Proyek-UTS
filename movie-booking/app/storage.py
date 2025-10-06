from typing import Dict, List, Set, Tuple
from .schemas import Movie, Showtime, SeatStatus
from .utils import seat_codes
import itertools

# ---------- penyimpanan in-memory ----------
_movies: Dict[int, Movie] = {}
_showtimes: Dict[int, Showtime] = {}
_seats_status: Dict[int, Dict[str, SeatStatus]] = {}        # showtime_id -> seat_code -> status
_booked_seats: Dict[int, Set[str]] = {}
_carts: Dict[str, List[Tuple[str, int, List[str]]]] = {}    # user_id -> [(cart_item_id, showtime_id, seats)]

# metadata layout per showtime
_showtime_meta: Dict[int, Dict] = {}  # id -> {"aisles": List[int], "vip": set(), "disabled": set()}

# ---------- id generator ----------
_movie_id_counter = itertools.count(1)
_showtime_id_counter = itertools.count(1)
def next_movie_id() -> int: return next(_movie_id_counter)
def next_showtime_id() -> int: return next(_showtime_id_counter)

# ---------- movie ops ----------
def save_movie(m: Movie) -> Movie:
    _movies[m.id] = m
    return m

def get_movie(movie_id: int) -> Movie | None: return _movies.get(movie_id)
def list_movies() -> List[Movie]: return list(_movies.values())

def delete_movie(movie_id: int) -> bool:
    if movie_id not in _movies:
        return False
    for sid, st in list(_showtimes.items()):
        if st.movie_id == movie_id:
            _showtimes.pop(sid, None)
            _seats_status.pop(sid, None)
            _booked_seats.pop(sid, None)
            _showtime_meta.pop(sid, None)
    _movies.pop(movie_id, None)
    return True

# ---------- showtime ops ----------
def save_showtime(st: Showtime) -> Showtime:
    _showtimes[st.id] = st

    # init seat map (default available)
    seat_map = {code: SeatStatus.available for code in seat_codes(st.rows, st.cols)}

    # metadata: aisles/vip/disabled
    aisles = list(st.aisles_cols or [])
    vip = set(st.vip_seats or [])
    disabled = set(st.disabled_seats or [])

    # tandai kursi disabled sebagai blocked
    for code in disabled:
        if code in seat_map:
            seat_map[code] = SeatStatus.blocked

    _seats_status[st.id] = seat_map
    _booked_seats[st.id] = set()
    _showtime_meta[st.id] = {"aisles": aisles, "vip": vip, "disabled": disabled}
    return st

def list_showtimes(movie_id: int | None = None) -> List[Showtime]:
    sts = list(_showtimes.values())
    return [s for s in sts if movie_id is None or s.movie_id == movie_id]

def get_showtime(showtime_id: int) -> Showtime | None: return _showtimes.get(showtime_id)
def seats_map(showtime_id: int): return _seats_status.get(showtime_id)
def showtime_meta(showtime_id: int): return _showtime_meta.get(showtime_id)

# ---------- cart ops ----------
def get_cart(user_id: str) -> List[tuple[str, int, List[str]]]:
    return _carts.get(user_id, [])

def set_cart(user_id: str, items: List[tuple[str, int, List[str]]]) -> None:
    _carts[user_id] = items
