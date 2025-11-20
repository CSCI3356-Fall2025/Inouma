import datetime as dt

def daterange(start_date, end_date):
    d = start_date
    while d <= end_date:
        yield d
        d += dt.timedelta(days=1)

def overlaps(a_start, a_end, b_start, b_end):
    return not (a_end <= b_start or a_start >= b_end)