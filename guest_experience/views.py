from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from django.db.models import Count, Q
from django.db.models.functions import TruncDate
import json
import pandas as pd
from datetime import datetime, timedelta
from .models import ArrivalRecord
from django.db import models


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def dashboard(request):
    """
    Guest Experience - Arrivals Dashboard with charts and metrics.
    """
    today = timezone.localdate()
    
    # Get filter parameters
    start_date = request.GET.get('start_date', (today - timedelta(days=30)).isoformat())
    end_date = request.GET.get('end_date', today.isoformat())
    status_filter = request.GET.get('status', '')
    country_filter = request.GET.get('country', '')
    travel_agent_filter = request.GET.get('travel_agent', '')
    search_query = request.GET.get('search', '')
    
    try:
        start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
        end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start_date_obj = today - timedelta(days=30)
        end_date_obj = today
        start_date = start_date_obj.isoformat()
        end_date = end_date_obj.isoformat()

    # Build base queryset for dropdown options (from current date range)
    base_qs = ArrivalRecord.objects.filter(
        arrival_date__gte=start_date_obj,
        arrival_date__lte=end_date_obj,
    )
    # Optionally respect current status/country filters when building dropdown
    if status_filter:
        base_qs = base_qs.filter(status__iexact=status_filter)
    if country_filter:
        base_qs = base_qs.filter(country__icontains=country_filter)

    travel_agents = (
        base_qs.exclude(travel_agent_name__isnull=True)
        .exclude(travel_agent_name="")
        .values_list("travel_agent_name", flat=True)
        .order_by("travel_agent_name")
        .distinct()
    )
    
    context = {
        "section": "guest_experience",
        "subsection": "dashboard",
        "page_title": "Guest Experience - Arrivals Dashboard",
        "today": today,
        "start_date": start_date,
        "end_date": end_date,
        "status_filter": status_filter,
        "country_filter": country_filter,
        "travel_agent_filter": travel_agent_filter,
        "search_query": search_query,
        "travel_agents": travel_agents,
    }
    return render(request, "guest_experience/dashboard.html", context)


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
def edit_arrival(request, confirmation_number):
    """
    Edit an arrival record by confirmation number.
    GET: Returns JSON with record data
    POST: Updates the record
    """
    try:
        record = ArrivalRecord.objects.get(confirmation_number=confirmation_number)
    except ArrivalRecord.DoesNotExist:
        return JsonResponse({"error": "Record not found"}, status=404)

    if request.method == "GET":
        # Return record data for editing
        return JsonResponse({
            "confirmation_number": record.confirmation_number,
            "room": record.room or "",
            "first_name": record.first_name or "",
            "last_name": record.last_name or "",
            "guest_name": record.guest_name or "",
            "phone": record.phone or "",
            "email": record.email or "",
            "nationality": record.nationality or "",
            "country": record.country or "",
            "arrival_date": record.arrival_date.isoformat() if record.arrival_date else "",
            "departure_date": record.departure_date.isoformat() if record.departure_date else "",
            "travel_agent_name": record.travel_agent_name or "",
            "status": record.status or "",
            "eta": record.eta or "",
        })

    elif request.method == "POST":
        # Update the record
        try:
            payload = json.loads(request.body.decode("utf-8") or "{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        # Update fields
        if "room" in payload:
            record.room = payload["room"].strip() or None
        if "first_name" in payload:
            record.first_name = payload["first_name"].strip()
        if "last_name" in payload:
            record.last_name = payload["last_name"].strip()
        if "guest_name" in payload:
            record.guest_name = payload["guest_name"].strip()
        elif "first_name" in payload or "last_name" in payload:
            # Auto-update guest_name if first/last name changed
            first = record.first_name or ""
            last = record.last_name or ""
            record.guest_name = (first + " " + last).strip()
        if "phone" in payload:
            record.phone = payload["phone"].strip()
        if "email" in payload:
            record.email = payload["email"].strip()
        if "nationality" in payload:
            record.nationality = payload["nationality"].strip()
        if "country" in payload:
            record.country = payload["country"].strip()
        if "arrival_date" in payload:
            try:
                if payload["arrival_date"]:
                    record.arrival_date = timezone.datetime.strptime(payload["arrival_date"], "%Y-%m-%d").date()
                else:
                    record.arrival_date = None
            except (ValueError, TypeError):
                pass
        if "departure_date" in payload:
            try:
                if payload["departure_date"]:
                    record.departure_date = timezone.datetime.strptime(payload["departure_date"], "%Y-%m-%d").date()
                else:
                    record.departure_date = None
            except (ValueError, TypeError):
                pass
        if "travel_agent_name" in payload:
            record.travel_agent_name = payload["travel_agent_name"].strip()
        if "status" in payload:
            record.status = payload["status"].strip()
        if "eta" in payload:
            record.eta = payload["eta"].strip()

        # Recalculate nights if dates changed
        if record.arrival_date and record.departure_date:
            try:
                diff = (record.departure_date - record.arrival_date).days
                record.nights = diff if diff >= 0 else None
            except Exception:
                pass

        record.updated_by = request.user
        record.updated_at = timezone.now()
        record.save()

        return JsonResponse({
            "success": True,
            "message": "Record updated successfully",
            "confirmation_number": record.confirmation_number
        })


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

    now = timezone.now()
    updated = 0
    qs = ArrivalRecord.objects.filter(confirmation_number__in=cleaned_ids)
    for record in qs:
        # Only set in-house timing if actually transitioning to In-House
        if (record.status or "").lower() not in ["in-house", "in house"]:
            record.status = "In-House"
            record.in_house_since = now
            record.in_house_by = request.user

            # First courtesy call: 20 minutes after status change
            record.first_courtesy_due_at = now + timedelta(minutes=20)

            # Second courtesy call: next day if stay > 1 night and before departure
            second_due = None
            if record.nights and record.nights > 1:
                candidate = now + timedelta(days=1)
                if record.departure_date:
                    # Only schedule if still before departure date
                    if candidate.date() <= record.departure_date:
                        second_due = candidate
                else:
                    second_due = candidate
            record.second_courtesy_due_at = second_due

        record.updated_by = request.user
        record.updated_at = now
        record.save()
        updated += 1

    return JsonResponse({"updated": updated})


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def courtesy_calls(request):
    """
    Page to track courtesy calls for in-house guests.
    """
    today = timezone.localdate()
    context = {
        "section": "guest_experience",
        "subsection": "courtesy_calls",
        "page_title": "Guest Experience - Courtesy Calls",
        "today": today,
    }
    return render(request, "guest_experience/courtesy_calls.html", context)


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def courtesy_calls_dashboard(request):
    """
    Courtesy Calls dashboard with filters and summary metrics.
    Uses courtesy_calls_api data on the frontend.
    """
    today = timezone.localdate()
    context = {
        "section": "guest_experience",
        "subsection": "courtesy_calls",
        "page_title": "Guest Experience - Courtesy Calls Dashboard",
        "today": today,
    }
    return render(request, "guest_experience/courtesy_calls_dashboard.html", context)


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
            "in_house_since": a.in_house_since.isoformat() if a.in_house_since else None,
            "in_house_by": a.in_house_by.username if a.in_house_by else None,
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


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def courtesy_calls_api(request):
    """
    API endpoint for courtesy call tracking.
    Shows in-house guests and their courtesy call due/completed state.
    """
    now = timezone.now()

    qs = ArrivalRecord.objects.filter(
        models.Q(status__iexact="In-House") | models.Q(status__iexact="in house")
    ).order_by("room")

    data = []
    for a in qs:
        # First courtesy status
        first_status = "Not Scheduled"
        if a.first_courtesy_due_at:
            if a.first_courtesy_done_at:
                first_status = "Completed"
            elif a.first_courtesy_due_at <= now:
                first_status = "Overdue"
            else:
                first_status = "Pending"

        # Second courtesy status
        second_status = "Not Scheduled"
        if a.second_courtesy_due_at:
            if a.second_courtesy_done_at:
                second_status = "Completed"
            elif a.second_courtesy_due_at <= now:
                second_status = "Overdue"
            else:
                second_status = "Pending"

        data.append(
            {
                "room": a.room,
                "guest_name": a.guest_name,
                "confirmation_number": a.confirmation_number,
                "phone": a.phone,
                "country": a.country,
                "arrival_date": a.arrival_date.isoformat() if a.arrival_date else None,
                "departure_date": a.departure_date.isoformat() if a.departure_date else None,
                "nights": a.nights,
                "in_house_since": a.in_house_since.isoformat() if a.in_house_since else None,
                "in_house_by": a.in_house_by.username if a.in_house_by else None,
                "first_courtesy_due_at": a.first_courtesy_due_at.isoformat() if a.first_courtesy_due_at else None,
                "first_courtesy_done_at": a.first_courtesy_done_at.isoformat() if a.first_courtesy_done_at else None,
                "first_courtesy_by": a.first_courtesy_by.username if a.first_courtesy_by else None,
                "first_courtesy_status": first_status,
                "first_courtesy_outcome": a.first_courtesy_outcome,
                "first_courtesy_notes": a.first_courtesy_notes,
                "second_courtesy_due_at": a.second_courtesy_due_at.isoformat() if a.second_courtesy_due_at else None,
                "second_courtesy_done_at": a.second_courtesy_done_at.isoformat() if a.second_courtesy_done_at else None,
                "second_courtesy_by": a.second_courtesy_by.username if a.second_courtesy_by else None,
                "second_courtesy_status": second_status,
                "second_courtesy_outcome": a.second_courtesy_outcome,
                "second_courtesy_notes": a.second_courtesy_notes,
            }
        )

    return JsonResponse({"results": data})


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
@require_POST
def mark_courtesy_done(request):
    """
    Mark a courtesy call as completed.
    Expects JSON:
      {
        "confirmation_number": "...",
        "which": "first"|"second",
        "outcome": "...",
        "notes": "..."
      }
    """
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    confirmation_number = str(payload.get("confirmation_number") or "").strip()
    which = str(payload.get("which") or "").strip().lower()
    outcome = str(payload.get("outcome") or "").strip()
    notes = str(payload.get("notes") or "").strip()
    if not confirmation_number or which not in {"first", "second"}:
        return JsonResponse({"error": "Invalid parameters"}, status=400)

    try:
        record = ArrivalRecord.objects.get(confirmation_number=confirmation_number)
    except ArrivalRecord.DoesNotExist:
        return JsonResponse({"error": "Record not found"}, status=404)

    now = timezone.now()
    if which == "first":
        record.first_courtesy_done_at = now
        record.first_courtesy_by = request.user
        record.first_courtesy_outcome = outcome
        record.first_courtesy_notes = notes
    else:
        record.second_courtesy_done_at = now
        record.second_courtesy_by = request.user
        record.second_courtesy_outcome = outcome
        record.second_courtesy_notes = notes
    record.updated_by = request.user
    record.updated_at = now
    record.save()

    return JsonResponse({"success": True})


@login_required
@permission_required("accounts.view_hotel_management", raise_exception=True)
def dashboard_api(request):
    """
    API endpoint for dashboard data including metrics and chart data.
    """
    today = timezone.localdate()
    
    # Get filter parameters
    start_date_str = request.GET.get('start_date', (today - timedelta(days=30)).isoformat())
    end_date_str = request.GET.get('end_date', today.isoformat())
    status_filter = request.GET.get('status', '')
    country_filter = request.GET.get('country', '')
    travel_agent_filter = request.GET.get('travel_agent', '')
    search_query = request.GET.get('search', '')
    
    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        start_date = today - timedelta(days=30)
        end_date = today
    
    # Base queryset
    qs = ArrivalRecord.objects.filter(
        arrival_date__gte=start_date,
        arrival_date__lte=end_date
    )
    
    # Apply filters
    if status_filter:
        qs = qs.filter(status__iexact=status_filter)
    
    if country_filter:
        qs = qs.filter(country__icontains=country_filter)
    
    if travel_agent_filter:
        qs = qs.filter(travel_agent_name__icontains=travel_agent_filter)
    
    if search_query:
        qs = qs.filter(
            Q(guest_name__icontains=search_query) |
            Q(confirmation_number__icontains=search_query) |
            Q(room__icontains=search_query) |
            Q(phone__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(travel_agent_name__icontains=search_query)
        )
    
    # Calculate metrics
    total_arrivals = qs.count()
    
    # Status breakdown
    status_breakdown = qs.values('status').annotate(count=Count('id')).order_by('-count')
    status_data = {item['status'] or 'Unknown': item['count'] for item in status_breakdown}
    
    # Country breakdown (top 10)
    country_breakdown = qs.exclude(country__isnull=True).exclude(country='').values('country').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    country_data = {item['country']: item['count'] for item in country_breakdown}
    
    # Daily arrivals trend
    daily_trend = qs.annotate(date=TruncDate('arrival_date')).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    daily_trend_data = {
        'labels': [item['date'].isoformat() if item['date'] else '' for item in daily_trend],
        'data': [item['count'] for item in daily_trend]
    }
    
    # Nationality breakdown (top 10)
    nationality_breakdown = qs.exclude(nationality__isnull=True).exclude(nationality='').values('nationality').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    nationality_data = {item['nationality']: item['count'] for item in nationality_breakdown}
    
    # Travel agent breakdown (top 10)
    agent_breakdown = qs.exclude(travel_agent_name__isnull=True).exclude(travel_agent_name='').values('travel_agent_name').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    agent_data = {item['travel_agent_name']: item['count'] for item in agent_breakdown}
    
    # Expected vs In-House vs Departed
    expected_count = qs.filter(status__iexact='Expected').count()
    in_house_count = qs.filter(
        models.Q(status__iexact='In-House') | models.Q(status__iexact='in house')
    ).count()
    departed_count = qs.filter(status__iexact='Departed').count()
    
    # Average nights
    avg_nights = qs.exclude(nights__isnull=True).aggregate(
        avg_nights=models.Avg('nights')
    )['avg_nights'] or 0
    
    return JsonResponse({
        'metrics': {
            'total_arrivals': total_arrivals,
            'expected': expected_count,
            'in_house': in_house_count,
            'departed': departed_count,
            'avg_nights': round(avg_nights, 1) if avg_nights else 0,
        },
        'charts': {
            'status_breakdown': status_data,
            'country_breakdown': country_data,
            'nationality_breakdown': nationality_data,
            'agent_breakdown': agent_data,
            'daily_trend': daily_trend_data,
        }
    })
