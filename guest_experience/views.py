from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
import json
import pandas as pd
from .models import ArrivalRecord
from django.db import models


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def dashboard(request):
    """
    Simple redirect so that /guest-experience/ opens the Arrivals view.
    """
    return redirect("guest_experience:arrivals")


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def arrivals(request):
    """
    Guest Experience - Arrivals page.
    Currently uses placeholder data; wire to your PMS data later.
    """
    today = timezone.localdate()
    context = {
        "section": "guest_experience",
        "subsection": "arrivals",
        "page_title": "Guest Experience - Arrivals",
        "today": today,
    }
    return render(request, "guest_experience/arrivals.html", context)


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def upload_arrivals(request):
    """
    Upload an Excel file (e.g. 'Arrival reporte.xlsx') to populate ArrivalRecord.

    Expected columns (case-insensitive):
      - Room
      - Guest Name
      - ETA
      - Nights
      - Status
      - Arrival Date
    """
    if request.method != "POST":
        return redirect("guest_experience:arrivals")

    file = request.FILES.get("file")
    if not file:
        messages.error(request, "Please choose an Excel file to upload.")
        return redirect("guest_experience:arrivals")

    try:
        # Read without assuming the first row is the header, so we can detect the real header row
        raw_df = pd.read_excel(file, header=None)
    except Exception as exc:
        messages.error(request, f"Could not read Excel file: {exc}")
        return redirect("guest_experience:arrivals")

    # Try to detect the header row by looking for a cell equal to 'Arrival Date' (case-insensitive)
    header_row_idx = None
    target_header = "arrival date"
    for idx, row in raw_df.iterrows():
        for val in row:
            if isinstance(val, str) and val.strip().lower() == target_header:
                header_row_idx = idx
                break
        if header_row_idx is not None:
            break

    if header_row_idx is None:
        # Fallback: treat the first row as header
        header_row_idx = 0

    header = raw_df.iloc[header_row_idx].tolist()
    df = raw_df.iloc[header_row_idx + 1 :].copy()

    # Normalize column names for flexible matching
    df.columns = [str(c).strip().lower() for c in header]

    def col(*names):
        for n in names:
            n = n.lower()
            if n in df.columns:
                return n
        return None

    # Map your Excel headers
    property_col = col("property")
    confirmation_col = col("confirmation number", "confirmation")
    first_name_col = col("first name", "firstname", "first")
    last_name_col = col("last name", "lastname", "last")
    room_col = col("room number", "room")
    phone_col = col("phone", "phone number", "tel")
    email_col = col("email", "e-mail")
    nationality_col = col("nationality")
    country_col = col("country")
    guest_col = col("guest name", "guest", "name")
    first_name_col = col("first name", "firstname", "first")
    last_name_col = col("last name", "lastname", "last")
    eta_col = col("eta", "arrival time")
    nights_col = col("nights", "length of stay")
    status_col = col("status")
    arrival_date_col = col("arrival date", "check in", "arrival")
    departure_date_col = col("departure date", "check out", "checkout", "departure")

    # We must at least have arrival date; room number is optional
    if not arrival_date_col:
        messages.error(
            request,
            "Excel file must contain an 'Arrival Date' column.",
        )
        return redirect("guest_experience:arrivals")

    # If we have confirmation numbers, clean existing rows for those confirmations
    # so re-importing the same Excel file does not create duplicates.
    if confirmation_col:
        confirmation_values = set()
        for _, row in df.iterrows():
            cn = str(row.get(confirmation_col) or "").strip()
            if cn:
                confirmation_values.add(cn)
        if confirmation_values:
            ArrivalRecord.objects.filter(confirmation_number__in=confirmation_values).delete()

    created_or_updated = 0
    today = timezone.localdate()
    for _, row in df.iterrows():
        arrival_date_val = row.get(arrival_date_col)
        if pd.isna(arrival_date_val):
            continue
        try:
            arrival_date = pd.to_datetime(arrival_date_val).date()
        except Exception:
            # Skip rows with bad dates
            continue

        property_name = str(row.get(property_col) or "").strip() if property_col else ""
        confirmation_number = str(row.get(confirmation_col) or "").strip() if confirmation_col else ""
        first_name = str(row.get(first_name_col) or "").strip() if first_name_col else ""
        last_name = str(row.get(last_name_col) or "").strip() if last_name_col else ""
        room = str(row.get(room_col) or "").strip() if room_col else ""
        phone = str(row.get(phone_col) or "").strip() if phone_col else ""
        email = str(row.get(email_col) or "").strip() if email_col else ""
        nationality = str(row.get(nationality_col) or "").strip() if nationality_col else ""
        country = str(row.get(country_col) or "").strip() if country_col else ""

        # Build guest name from either a combined column or First/Last Name
        if guest_col:
            guest_name = str(row.get(guest_col) or "").strip()
        else:
            first = str(row.get(first_name_col) or "").strip() if first_name_col else ""
            last = str(row.get(last_name_col) or "").strip() if last_name_col else ""
            guest_name = (first + " " + last).strip()

        eta = "" if not eta_col else str(row.get(eta_col) or "").strip()

        # Departure date (store raw date if present)
        departure_date = None
        if departure_date_col:
            dep_val_for_store = row.get(departure_date_col)
            if pd.notna(dep_val_for_store):
                try:
                    departure_date = pd.to_datetime(dep_val_for_store).date()
                except Exception:
                    departure_date = None

        # Nights: from explicit column if present, otherwise compute from Arrival/Departure
        nights = None
        if nights_col:
            nights_raw = row.get(nights_col)
            try:
                nights = int(nights_raw) if pd.notna(nights_raw) else None
            except (TypeError, ValueError):
                nights = None
        elif departure_date is not None:
            try:
                diff = (departure_date - arrival_date).days
                nights = diff if diff >= 0 else None
            except Exception:
                nights = None

        # Status: from column; default to "Expected" if blank
        raw_status = "" if not status_col else str(row.get(status_col) or "").strip()
        status = raw_status or "Expected"

        # If no confirmation number, skip to avoid untrackable duplicates
        if not confirmation_number:
            continue

        ArrivalRecord.objects.create(
            # Raw columns
            property_name=property_name,
            confirmation_number=confirmation_number,
            first_name=first_name,
            last_name=last_name,
            room=room or None,
            phone=phone,
            email=email,
            nationality=nationality,
            country=country,
            arrival_date=arrival_date,
            departure_date=departure_date,
            travel_agent_name=str(row.get(col("travel agent name", "agent", "travel agent")) or "").strip(),
            # Derived/display
            guest_name=guest_name,
            eta=eta,
            nights=nights,
            status=status,
            created_by=request.user,
            updated_by=request.user,
        )
        created_or_updated += 1

    messages.success(
        request,
        f"Imported {created_or_updated} arrival rows from Excel.",
    )
    return redirect("guest_experience:arrivals")


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def in_house(request):
    """
    Guest Experience - In-House Guests page.
    """
    today = timezone.localdate()
    context = {
        "section": "guest_experience",
        "subsection": "in_house",
        "page_title": "Guest Experience - In-House Guests",
        "today": today,
    }
    return render(request, "guest_experience/in_house.html", context)


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def departures(request):
    """
    Guest Experience - Departures page.
    """
    today = timezone.localdate()
    context = {
        "section": "guest_experience",
        "subsection": "departures",
        "page_title": "Guest Experience - Departures",
        "today": today,
    }
    return render(request, "guest_experience/departures.html", context)


# --- Simple JSON API placeholders ---

@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def arrivals_api(request):
    """
    API endpoint for arrivals.
    Returns arrivals from ArrivalRecord for today (or ?date=YYYY-MM-DD).
    """
    date_param = request.GET.get("date")
    try:
        if date_param:
            target_date = timezone.datetime.strptime(date_param, "%Y-%m-%d").date()
        else:
            target_date = timezone.localdate()
    except ValueError:
        return JsonResponse({"error": "Invalid date format, expected YYYY-MM-DD."}, status=400)

    # Exclude records with "In-House" status (case-insensitive, handles both "In-House" and "in house")
    qs = ArrivalRecord.objects.filter(
        arrival_date=target_date
    ).exclude(
        models.Q(status__iexact="in-house") | models.Q(status__iexact="in house")
    ).order_by("room")
    data = []
    for a in qs:
        data.append(
            {
                "room": a.room,
                "guest_name": a.guest_name,
                "eta": a.eta,
                "nights": a.nights,
                "status": a.status,
                "property_name": a.property_name,
                "confirmation_number": a.confirmation_number,
                "first_name": a.first_name,
                "last_name": a.last_name,
                "phone": a.phone,
                "email": a.email,
                "nationality": a.nationality,
                "country": a.country,
                "arrival_date": a.arrival_date.isoformat() if a.arrival_date else None,
                "departure_date": a.departure_date.isoformat() if a.departure_date else None,
                "travel_agent_name": a.travel_agent_name,
            }
        )
    return JsonResponse({"results": data})


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
@require_POST
def delete_arrivals(request):
    """
    Bulk delete arrivals by confirmation numbers.
    Expects JSON body: {"confirmation_numbers": ["ABC123", "DEF456", ...]}
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    ids = payload.get("confirmation_numbers") or []
    if not isinstance(ids, list):
        return JsonResponse({"error": "confirmation_numbers must be a list"}, status=400)

    # Normalize and filter out empty values
    cleaned_ids = [str(x).strip() for x in ids if str(x).strip()]
    if not cleaned_ids:
        return JsonResponse({"deleted": 0})

    deleted_count, _ = ArrivalRecord.objects.filter(confirmation_number__in=cleaned_ids).delete()
    return JsonResponse({"deleted": deleted_count})


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
@require_POST
def mark_in_house(request):
    """
    Bulk update arrivals to In-House status by confirmation numbers.
    Expects JSON body: {"confirmation_numbers": ["ABC123", "DEF456", ...]}
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    ids = payload.get("confirmation_numbers") or []
    if not isinstance(ids, list):
        return JsonResponse({"error": "confirmation_numbers must be a list"}, status=400)

    cleaned_ids = [str(x).strip() for x in ids if str(x).strip()]
    if not cleaned_ids:
        return JsonResponse({"updated": 0})

    updated = ArrivalRecord.objects.filter(
        confirmation_number__in=cleaned_ids
    ).update(status="In-House", updated_by=request.user, updated_at=timezone.now())

    return JsonResponse({"updated": updated})


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def in_house_api(request):
    """
    API endpoint for in-house guests.
    Returns guests whose status is 'In-House' for a given date (default: today).
    """
    date_param = request.GET.get("date")
    try:
        if date_param:
            target_date = timezone.datetime.strptime(date_param, "%Y-%m-%d").date()
        else:
            target_date = timezone.localdate()
    except ValueError:
        return JsonResponse({"error": "Invalid date format, expected YYYY-MM-DD."}, status=400)

    # In-house: status In-House (case-insensitive, handles both "In-House" and "in house")
    qs = ArrivalRecord.objects.filter(
        models.Q(status__iexact="in-house") | models.Q(status__iexact="in house")
    )
    qs = qs.filter(
        arrival_date__lte=target_date
    ).filter(
        models.Q(departure_date__isnull=True) | models.Q(departure_date__gte=target_date)
    ).order_by("room")

    data = [
        {
            "room": a.room,
            "guest_name": a.guest_name,
            "confirmation_number": a.confirmation_number,
            "phone": a.phone,
            "country": a.country,
            "travel_agent_name": a.travel_agent_name,
            "arrival_date": a.arrival_date.isoformat() if a.arrival_date else None,
            "departure_date": a.departure_date.isoformat() if a.departure_date else None,
            "nights": a.nights,
            "status": a.status,
        }
        for a in qs
    ]
    return JsonResponse({"results": data})


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def departures_api(request):
    """
    API endpoint for departures.
    """
    sample = [
        {
            "room": "207",
            "guest_name": "Leaving Guest",
            "checkout_time": "11:00",
            "balance": 0.0,
            "status": "Due Out",
        }
    ]
    return JsonResponse({"results": sample})
