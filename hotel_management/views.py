from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.utils import timezone
from django.db.models import Avg, Sum, Q
from django.http import JsonResponse
from .models import Hotel, Competitor, DailyData, CompetitorData, AuditLog, MarketSummary, PerformanceIndex, BudgetGoal
from datetime import timedelta, datetime, date
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
import json


@login_required
@permission_required('accounts.view_hotel_management', raise_exception=True)
def budget_goals(request):
    """Simple view to render Budget & KPI Goals template (placeholder backend)."""
    hotel = Hotel.objects.first()
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')

    fiscal_year = timezone.now().year
    if request.method == 'POST':
        # Helper: permission to unlock
        def user_can_unlock(user):
            try:
                profile = getattr(user, 'profile', None)
                is_profile_admin = bool(getattr(profile, 'is_admin', False))
                return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False) or is_profile_admin)
            except Exception:
                return False

        # Deletion path
        if request.POST.get('action') == 'delete' and request.POST.get('goal_id'):
            try:
                goal = BudgetGoal.objects.get(id=request.POST.get('goal_id'), hotel=hotel)
                goal.delete()
                messages.success(request, 'Goal deleted successfully.')
            except BudgetGoal.DoesNotExist:
                messages.error(request, 'Goal not found.')
        # Unlock path (admins/privileged only)
        elif request.POST.get('action') == 'unlock' and request.POST.get('goal_id'):
            try:
                goal = BudgetGoal.objects.get(id=request.POST.get('goal_id'), hotel=hotel)
                if user_can_unlock(request.user) or goal.created_by_id == request.user.id:
                    goal.lock_targets = False
                    goal.save(update_fields=['lock_targets'])
                    messages.success(request, 'Goal unlocked successfully.')
                else:
                    messages.error(request, 'You do not have permission to unlock this goal.')
            except BudgetGoal.DoesNotExist:
                messages.error(request, 'Goal not found.')
        else:
            fiscal_year = int(request.POST.get('fiscal_year')) if request.POST.get('fiscal_year') else timezone.now().year
            period_type = request.POST.get('period_type', 'annual')
            period_detail = request.POST.get('period_detail', '')

            # Find or create the record for this period
            bg, _ = BudgetGoal.objects.get_or_create(
                hotel=hotel,
                fiscal_year=fiscal_year,
                period_type=period_type,
                period_detail=period_detail
            )

            if bg.lock_targets:
                messages.warning(request, 'Goals are locked for this period and cannot be modified.')
            else:
                # Update fields
                bg.occupancy_goal = request.POST.get('occupancy_goal') or None
                bg.adr_goal = request.POST.get('adr_goal') or None
                bg.revpar_goal = request.POST.get('revpar_goal') or None
                bg.total_revenue_budget = request.POST.get('total_revenue_budget') or None
                bg.mpi_goal = request.POST.get('mpi_goal') or None
                bg.ari_goal = request.POST.get('ari_goal') or None
                bg.rgi_goal = request.POST.get('rgi_goal') or None
                bg.notes = request.POST.get('notes', '')
                bg.lock_targets = True if request.POST.get('lock_targets') else False
                bg.updated_by = request.user
                if not bg.created_by:
                    bg.created_by = request.user
                bg.save()
                messages.success(request, 'Budget & KPI Goals saved successfully.')

    # Determine which record to load for editing/display
    qs = BudgetGoal.objects.filter(hotel=hotel)
    # Optional filters
    if request.GET.get('fiscal_year'):
        qs = qs.filter(fiscal_year=request.GET.get('fiscal_year'))
    if request.GET.get('period_type'):
        qs = qs.filter(period_type=request.GET.get('period_type'))
    if request.GET.get('period_detail'):
        qs = qs.filter(period_detail=request.GET.get('period_detail'))
    goals = qs.order_by('-fiscal_year', 'period_type', 'period_detail').first()

    goals_list = BudgetGoal.objects.filter(hotel=hotel).order_by('-fiscal_year', 'period_type', 'period_detail')

    # Annotate per-goal unlock permission for current user
    def user_can_unlock(user):
        try:
            profile = getattr(user, 'profile', None)
            is_profile_admin = bool(getattr(profile, 'is_admin', False))
            return bool(getattr(user, 'is_superuser', False) or getattr(user, 'is_staff', False) or is_profile_admin)
        except Exception:
            return False
    for g in goals_list:
        try:
            g.can_unlock_for_user = bool(g.lock_targets and (user_can_unlock(request.user) or (g.created_by_id == getattr(request.user, 'id', None))))
        except Exception:
            g.can_unlock_for_user = False

    # Quick metrics for header cards
    from django.db.models import Avg, Sum, Count
    aggregates = goals_list.aggregate(
        total_goals=Count('id'),
        active_goals=Count('id', filter=Q(lock_targets=False)),
        avg_occupancy=Avg('occupancy_goal'),
        total_revenue=Sum('total_revenue_budget'),
    )

    context = {
        'hotel': hotel,
        'fiscal_year': goals.fiscal_year if goals else fiscal_year,
        'period_type': getattr(goals, 'period_type', ''),
        'period_detail': getattr(goals, 'period_detail', ''),
        'occupancy_goal': getattr(goals, 'occupancy_goal', ''),
        'adr_goal': getattr(goals, 'adr_goal', ''),
        'revpar_goal': getattr(goals, 'revpar_goal', ''),
        'total_revenue_budget': getattr(goals, 'total_revenue_budget', ''),
        'mpi_goal': getattr(goals, 'mpi_goal', ''),
        'ari_goal': getattr(goals, 'ari_goal', ''),
        'rgi_goal': getattr(goals, 'rgi_goal', ''),
        'notes': getattr(goals, 'notes', ''),
        'lock_targets_checked': 'checked' if getattr(goals, 'lock_targets', False) else '',
        'lock_targets': bool(getattr(goals, 'lock_targets', False)),
        'goals_list': goals_list,
        'goals_metrics': {
            'total_goals': aggregates.get('total_goals') or 0,
            'active_goals': aggregates.get('active_goals') or 0,
            'avg_occupancy': float(aggregates.get('avg_occupancy') or 0),
            'total_revenue': float(aggregates.get('total_revenue') or 0),
        },
        'can_unlock': user_can_unlock(request.user),
    }
    return render(request, 'hotel_management/budget_goals.html', context)


@login_required
@permission_required('accounts.view_hotel_management', raise_exception=True)
def budget_goals_tracker(request):
    hotel = Hotel.objects.first()
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')

    goals_qs = BudgetGoal.objects.filter(hotel=hotel).order_by('-fiscal_year', 'period_type', 'period_detail')

    context = {
        'hotel': hotel,
        'goals_list': goals_qs,
    }
    return render(request, 'hotel_management/budget_goals_tracker.html', context)


@login_required
@permission_required('accounts.view_hotel_management', raise_exception=True)
def ajax_metrics(request):
    """AJAX endpoint for fetching updated dashboard metrics"""
    hotel = Hotel.objects.first()
    if not hotel:
        return JsonResponse({'error': 'Hotel not found'}, status=404)
    
    # Get recent daily data (last 30 days)
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    recent_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=thirty_days_ago
    ).order_by('-date')
    
    # Calculate summary statistics
    summary = {
        'total_revenue': recent_data.aggregate(Sum('total_revenue'))['total_revenue__sum'] or 0,
        'avg_occupancy': recent_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0,
        'avg_rate': recent_data.aggregate(Avg('average_rate'))['average_rate__avg'] or 0,
        'avg_revpar': recent_data.aggregate(Avg('revpar'))['revpar__avg'] or 0,
    }
    
    return JsonResponse(summary)

@login_required
@permission_required('accounts.view_hotel_management', raise_exception=True)
def performance_indicators_api(request):
    """API endpoint for performance indicators"""
    hotel = Hotel.objects.first()
    
    if not hotel:
        return JsonResponse({'error': 'Hotel not found'}, status=404)
    
    # Get date range from request or use current month
    today = timezone.now().date()
    
    # Default: first day to last day of current month
    current_month = today.month
    current_year = today.year
    from calendar import monthrange
    _, last_day = monthrange(current_year, current_month)
    start_date = date(current_year, current_month, 1)
    end_date = date(current_year, current_month, last_day)
    
    # Get date parameters from request if provided
    if request.GET.get('start_date') and request.GET.get('end_date'):
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Invalid date format'}, status=400)
    
    # Get performance data for the specified date range
    recent_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('-date')
    
    # Get performance indices
    performance_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).order_by('-date')
    
    # Calculate average metrics
    avg_occupancy = recent_data.aggregate(Avg('occupancy_percentage'))['occupancy_percentage__avg'] or 0
    avg_rate_index = performance_indices.aggregate(Avg('ari'))['ari__avg'] or 0
    avg_revpar_index = performance_indices.aggregate(Avg('rgi'))['rgi__avg'] or 0
    avg_market_share = performance_indices.aggregate(Avg('actual_market_share'))['actual_market_share__avg'] or 0
    
    # Return performance indicators as JSON
    return JsonResponse({
        'occupancy': float(avg_occupancy),
        'rate_index': float(avg_rate_index),
        'revpar_index': float(avg_revpar_index),
        'market_share': float(avg_market_share)
    })

@login_required
@permission_required('accounts.view_hotel_management', raise_exception=True)
def home(request):
    """Home page view"""
    # Get the user's hotel
    hotel = Hotel.objects.first()
    
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # Get date range from request or use current month
    today = timezone.now().date()
    
    # Default: first day to last day of current month
    current_month = today.month
    current_year = today.year
    from calendar import monthrange
    _, last_day = monthrange(current_year, current_month)
    start_date = date(current_year, current_month, 1)
    end_date = date(current_year, current_month, last_day)
    
    # Handle date filter form submission
    if request.method == 'POST':
        try:
            start_date = datetime.strptime(request.POST.get('start_date'), '%Y-%m-%d').date()
            end_date = datetime.strptime(request.POST.get('end_date'), '%Y-%m-%d').date()
            
            # Validate date range
            if start_date > end_date:
                messages.error(request, 'Start date cannot be after end date')
                start_date = date(current_year, current_month, 1)
                end_date = date(current_year, current_month, last_day)
        except (ValueError, TypeError):
            messages.error(request, 'Invalid date format')
    
    # Calculate prior year date range (same period last year)
    days_diff = (end_date - start_date).days
    prior_year_start_date = date(start_date.year - 1, start_date.month, start_date.day)
    prior_year_end_date = prior_year_start_date + timedelta(days=days_diff)
    
    # Get aggregated data for current period
    current_period_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        avg_occupancy=Avg('occupancy_percentage'),
        avg_adr=Avg('average_rate'),
        avg_revpar=Avg('revpar'),
        total_revenue=Sum('total_revenue'),
        total_rooms_sold=Sum('rooms_sold')
    )
    
    # Get aggregated data for prior year (same period last year)
    prior_year_data = DailyData.objects.filter(
        hotel=hotel,
        date__gte=prior_year_start_date,
        date__lte=prior_year_end_date
    ).aggregate(
        avg_occupancy=Avg('occupancy_percentage'),
        avg_adr=Avg('average_rate'),
        avg_revpar=Avg('revpar'),
        total_revenue=Sum('total_revenue'),
        total_rooms_sold=Sum('rooms_sold')
    )
    
    # Safely calculate summary with fallbacks
    current_occ = current_period_data['avg_occupancy'] or 0
    prior_year_occ = prior_year_data['avg_occupancy'] or 0
    current_adr = current_period_data['avg_adr'] or 0
    prior_year_adr = prior_year_data['avg_adr'] or 0
    current_revpar = current_period_data['avg_revpar'] or 0
    prior_year_revpar = prior_year_data['avg_revpar'] or 0
    
    # Calculate changes safely
    occ_change = ((current_occ - prior_year_occ) / prior_year_occ * 100) if prior_year_occ != 0 else 0
    adr_change = ((current_adr - prior_year_adr) / prior_year_adr * 100) if prior_year_adr != 0 else 0
    revpar_change = ((current_revpar - prior_year_revpar) / prior_year_revpar * 100) if prior_year_revpar != 0 else 0
    
    summary = {
        'current_occ': current_occ,
        'prior_year_occ': prior_year_occ,
        'occ_change': occ_change,
        'current_adr': current_adr,
        'prior_year_adr': prior_year_adr,
        'adr_change': adr_change,
        'current_revpar': current_revpar,
        'prior_year_revpar': prior_year_revpar,
        'revpar_change': revpar_change,
    }
    
    # Get aggregated performance indices for current period
    current_period_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        date__gte=start_date,
        date__lte=end_date
    ).aggregate(
        avg_mpi=Avg('mpi'),
        avg_ari=Avg('ari'),
        avg_rgi=Avg('rgi'),
        avg_mpi_rank=Avg('mpi_rank'),
        avg_ari_rank=Avg('ari_rank'),
        avg_rgi_rank=Avg('rgi_rank')
    )
    
    # Get aggregated performance indices for prior year (same period last year)
    prior_year_indices = PerformanceIndex.objects.filter(
        hotel=hotel,
        date__gte=prior_year_start_date,
        date__lte=prior_year_end_date
    ).aggregate(
        avg_mpi=Avg('mpi'),
        avg_ari=Avg('ari'),
        avg_rgi=Avg('rgi'),
        avg_mpi_rank=Avg('mpi_rank'),
        avg_ari_rank=Avg('ari_rank'),
        avg_rgi_rank=Avg('rgi_rank')
    )
    
    # Safely get performance indices with fallbacks
    current_mpi = current_period_indices['avg_mpi'] or 0
    prior_year_mpi = prior_year_indices['avg_mpi'] or 0
    current_ari = current_period_indices['avg_ari'] or 0
    prior_year_ari = prior_year_indices['avg_ari'] or 0
    current_rgi = current_period_indices['avg_rgi'] or 0
    prior_year_rgi = prior_year_indices['avg_rgi'] or 0
    
    # Calculate changes safely
    mpi_change = ((current_mpi - prior_year_mpi) / prior_year_mpi * 100) if prior_year_mpi != 0 else 0
    ari_change = ((current_ari - prior_year_ari) / prior_year_ari * 100) if prior_year_ari != 0 else 0
    rgi_change = ((current_rgi - prior_year_rgi) / prior_year_rgi * 100) if prior_year_rgi != 0 else 0
    
    # Compute hotel's market rank vs competitors for the selected period
    competitor_avgs = PerformanceIndex.objects.filter(
        hotel=hotel,
        competitor__isnull=False,
        date__gte=start_date,
        date__lte=end_date
    ).values('competitor_id').annotate(
        c_mpi=Avg('mpi'),
        c_ari=Avg('ari'),
        c_rgi=Avg('rgi')
    )

    competitor_mpi_values = [row['c_mpi'] for row in competitor_avgs if row['c_mpi'] is not None]
    competitor_ari_values = [row['c_ari'] for row in competitor_avgs if row['c_ari'] is not None]
    competitor_rgi_values = [row['c_rgi'] for row in competitor_avgs if row['c_rgi'] is not None]

    def compute_rank(value, competitor_values):
        if value is None:
            return 0
        try:
            v = float(value)
        except (TypeError, ValueError):
            return 0
        higher = sum(1 for c in competitor_values if c is not None and float(c) > v)
        return higher + 1

    hotel_mpi_rank = compute_rank(current_mpi, competitor_mpi_values)
    hotel_ari_rank = compute_rank(current_ari, competitor_ari_values)
    hotel_rgi_rank = compute_rank(current_rgi, competitor_rgi_values)

    indices = {
        'current_mpi': current_mpi,
        'prior_year_mpi': prior_year_mpi,
        'mpi_change': mpi_change,
        'mpi_rank': hotel_mpi_rank,
        'current_ari': current_ari,
        'prior_year_ari': prior_year_ari,
        'ari_change': ari_change,
        'ari_rank': hotel_ari_rank,
        'current_rgi': current_rgi,
        'prior_year_rgi': prior_year_rgi,
        'rgi_change': rgi_change,
        'rgi_rank': hotel_rgi_rank,
        'total_competitors': Competitor.objects.filter(is_active=True).count()
    }
    
    # Get data for RevPAR positioning matrix - Current Period
    hotel_data = {
        'occupancy_index': current_mpi,
        'adr_index': current_ari
    }
    
    # Get aggregated competitor data for the matrix - Current Period
    competitor_data = []
    for comp in Competitor.objects.filter(is_active=True):
        comp_aggregated = CompetitorData.objects.filter(
            competitor=comp,
            date__gte=start_date,
            date__lte=end_date
        ).aggregate(
            avg_occupancy_index=Avg('occupancy_index'),
            avg_adr_index=Avg('adr_index')
        )
        
        if comp_aggregated['avg_occupancy_index'] and comp_aggregated['avg_adr_index']:
            competitor_data.append({
                'x': comp_aggregated['avg_occupancy_index'],
                'y': comp_aggregated['avg_adr_index'],
                'name': comp.name
            })
    
    # Get data for RevPAR positioning matrix - Previous Year
    prev_year_hotel_data = {
        'occupancy_index': prior_year_mpi,
        'adr_index': prior_year_ari
    }
    
    # Get aggregated competitor data for the matrix - Previous Year
    prev_year_competitor_data = []
    for comp in Competitor.objects.filter(is_active=True):
        prev_year_comp_aggregated = CompetitorData.objects.filter(
            competitor=comp,
            date__gte=prior_year_start_date,
            date__lte=prior_year_end_date
        ).aggregate(
            avg_occupancy_index=Avg('occupancy_index'),
            avg_adr_index=Avg('adr_index')
        )
        
        if prev_year_comp_aggregated['avg_occupancy_index'] and prev_year_comp_aggregated['avg_adr_index']:
            prev_year_competitor_data.append({
                'x': prev_year_comp_aggregated['avg_occupancy_index'],
                'y': prev_year_comp_aggregated['avg_adr_index'],
                'name': comp.name
            })
    
    from .json_utils import decimal_safe_dumps
    
    # Find the appropriate budget goal based on the date range
    def get_budget_goal_for_date_range(start_date, end_date):
        """Determine the appropriate budget goal based on date range"""
        # Calculate the duration of the date range
        days_diff = (end_date - start_date).days
        
        # Get the fiscal year (use the year of the start date)
        fiscal_year = start_date.year
        
        # Try to find the most appropriate budget goal based on date range
        try:
            # Get all goals for this hotel and fiscal year
            existing_goals = BudgetGoal.objects.filter(hotel=hotel, fiscal_year=fiscal_year)
            
            # Priority 1: Look for monthly goals that match the month
            if days_diff <= 31:  # Less than or equal to a month
                month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                # Check if start_date and end_date are in the same month
                if start_date.month == end_date.month and start_date.year == end_date.year:
                    period_detail = month_names[start_date.month - 1]
                    budget_goal = existing_goals.filter(
                        period_type='monthly',
                        period_detail=period_detail
                    ).first()
                    
                    if budget_goal:
                        return budget_goal

            # New: If the range spans multiple months within the same fiscal year, and no quarterly goal exists,
            # aggregate monthly goals weighted by days in range to form a synthetic goal
            if start_date.year == end_date.year and start_date.month != end_date.month:
                # Build list of months covered and the overlapping day counts
                from calendar import monthrange
                def month_iter(y, m_start, m_end):
                    for m in range(m_start, m_end + 1):
                        yield y, m
                total_days = (end_date - start_date).days + 1
                if total_days > 0:
                    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
                    weighted_occ_sum = 0.0
                    weighted_adr_sum = 0.0
                    covered_days = 0
                    months_covered_labels = []
                    for y, m in month_iter(start_date.year, start_date.month, end_date.month):
                        first_day = date(y, m, 1)
                        last_day = date(y, m, monthrange(y, m)[1])
                        overlap_start = max(start_date, first_day)
                        overlap_end = min(end_date, last_day)
                        if overlap_start <= overlap_end:
                            overlap_days = (overlap_end - overlap_start).days + 1
                            period_detail = month_names[m - 1]
                            goal = existing_goals.filter(period_type='monthly', period_detail=period_detail).first()
                            months_covered_labels.append(period_detail)
                            if goal and goal.occupancy_goal and goal.adr_goal:
                                try:
                                    weighted_occ_sum += float(goal.occupancy_goal) * overlap_days
                                    weighted_adr_sum += float(goal.adr_goal) * overlap_days
                                    covered_days += overlap_days
                                except (TypeError, ValueError):
                                    pass
                    if covered_days > 0:
                        agg_occ = weighted_occ_sum / covered_days
                        agg_adr = weighted_adr_sum / covered_days
                        agg_revpar = (agg_occ / 100.0) * agg_adr

                        class AggregateGoal:
                            def __init__(self, fiscal_year, period_detail, occ, adr, revpar):
                                self.fiscal_year = fiscal_year
                                self.period_type = 'monthly_aggregate'
                                self.period_detail = period_detail
                                self.occupancy_goal = occ
                                self.adr_goal = adr
                                self.revpar_goal = revpar
                                self.is_aggregate = True
                            def get_period_type_display(self):
                                return 'Monthly Aggregate'

                        label = f"{months_covered_labels[0]}–{months_covered_labels[-1]}"
                        return AggregateGoal(fiscal_year, label, agg_occ, agg_adr, agg_revpar)
            
            # Priority 2: Look for quarterly goals
            if days_diff <= 93:  # Less than or equal to a quarter
                quarter_num = (start_date.month - 1) // 3 + 1
                period_detail = f'Q{quarter_num}'
                budget_goal = existing_goals.filter(
                    period_type='quarter',
                    period_detail=period_detail
                ).first()
                
                if budget_goal:
                    return budget_goal
            
            # Priority 3: Look for annual goals
            budget_goal = existing_goals.filter(
                period_type='annual',
                period_detail=''
            ).first()
            
            if budget_goal:
                return budget_goal
            
            # Priority 4: If no exact match, try to find any goal that could be relevant
            # For monthly ranges, also check if there's a quarterly goal for that quarter
            if days_diff <= 31:
                quarter_num = (start_date.month - 1) // 3 + 1
                period_detail = f'Q{quarter_num}'
                budget_goal = existing_goals.filter(
                    period_type='quarter',
                    period_detail=period_detail
                ).first()
                
                if budget_goal:
                    return budget_goal
            
            return None
            
        except Exception as e:
            return None
    
    # Get the budget goal for the current date range
    budget_goal = get_budget_goal_for_date_range(start_date, end_date)
    
    # Calculate goal comparison metrics
    goal_comparison = {}
    if budget_goal and budget_goal.occupancy_goal and current_occ:
        goal_comparison['occupancy_diff'] = float(budget_goal.occupancy_goal) - float(current_occ)
        goal_comparison['occupancy_met'] = float(current_occ) >= float(budget_goal.occupancy_goal)
    
    context = {
        'hotel': hotel,
        'summary': summary,
        'indices': indices,
        'hotel_data': hotel_data,
        'competitor_data': decimal_safe_dumps(competitor_data),
        'start_date': start_date,
        'end_date': end_date,
        'prev_year_start_date': prior_year_start_date,
        'prev_year_end_date': prior_year_end_date,
        'prev_year_hotel_data': prev_year_hotel_data,
        'prev_year_competitor_data': decimal_safe_dumps(prev_year_competitor_data),
        'budget_goal': budget_goal,
        'goal_comparison': goal_comparison
    }
    
    return render(request, 'hotel_management/home.html', context)


def calculate_market_indices(date_str):
    """Calculate and store market performance indices for a specific date"""
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Use the utility function to update market summary and performance indices
        from .utils import update_market_summary, update_performance_rankings
        
        # Update market summary and performance indices
        update_market_summary(date_obj)
        
        # Update performance rankings
        update_performance_rankings(date_obj)
            
    except Exception as e:
        print(f"Error calculating market indices: {e}")
        # Don't raise the exception, just log it
        # This ensures data entry still works even if index calculation fails
@login_required
def data_entry(request):
    """View for data entry and management of hotel and competitor data"""
    # Allow users with either full hotel_management access or data_entry-only access
    if not (
        request.user.has_perm('accounts.view_hotel_management') or
        request.user.has_perm('accounts.view_data_entry')
    ):
        raise PermissionDenied
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.all().order_by('name')
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    # Handle POST requests for data entry and modifications
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'add_hotel_data':
            date_str = request.POST.get('date')
            rooms_sold = request.POST.get('rooms_sold')
            total_revenue = request.POST.get('total_revenue')
            notes = request.POST.get('notes', '')
            
            try:
                daily_data = DailyData.objects.create(
                    date=date_str,
                    hotel=hotel,
                    rooms_sold=rooms_sold,
                    total_revenue=total_revenue,
                    total_rooms=hotel.total_rooms,
                    notes=notes,
                    created_by=request.user
                )
                messages.success(request, f'Hotel data for {date_str} added successfully')
            except Exception as e:
                messages.error(request, f'Error saving hotel data: {str(e)}')
        
        elif action == 'add_competitor_data':
            date_str = request.POST.get('date')
            competitor_id = request.POST.get('competitor_id')
            rooms_sold = request.POST.get('rooms_sold')
            estimated_average_rate = request.POST.get('estimated_average_rate')
            notes = request.POST.get('notes', '')
            
            try:
                competitor = Competitor.objects.get(id=competitor_id)
                # Create the competitor data entry with basic fields
                comp_data = CompetitorData.objects.create(
                    date=date_str,
                    competitor=competitor,
                    rooms_sold=rooms_sold,
                    estimated_average_rate=estimated_average_rate,
                    total_rooms=competitor.total_rooms,
                    notes=notes,
                    created_by=request.user
                )
                
                # Calculate and update market performance indices
                calculate_market_indices(date_str)
                
                messages.success(request, f'Competitor data for {date_str} added successfully')
            except Exception as e:
                messages.error(request, f'Error saving competitor data: {str(e)}')
        
        elif action == 'edit_hotel_data':
            data_id = request.POST.get('hotel_data_id')
            date_str = request.POST.get('date')
            rooms_sold = request.POST.get('rooms_sold')
            total_revenue = request.POST.get('total_revenue')
            notes = request.POST.get('notes', '')
            
            try:
                daily_data = DailyData.objects.get(id=data_id)
                changes = {}
                
                if str(daily_data.date) != date_str:
                    changes['date'] = {'old': str(daily_data.date), 'new': date_str}
                if str(daily_data.rooms_sold) != rooms_sold:
                    changes['rooms_sold'] = {'old': daily_data.rooms_sold, 'new': int(rooms_sold)}
                if str(daily_data.total_revenue) != total_revenue:
                    changes['total_revenue'] = {'old': str(daily_data.total_revenue), 'new': total_revenue}
                if daily_data.notes != notes:
                    changes['notes'] = {'old': daily_data.notes, 'new': notes}
                
                if changes:
                    daily_data.date = date_str
                    daily_data.rooms_sold = rooms_sold
                    daily_data.total_revenue = total_revenue
                    daily_data.notes = notes
                    daily_data.save()
                    
                    AuditLog.objects.create(
                        entity_type='hotel_data',
                        entity_id=daily_data.id,
                        action='update',
                        changes=changes,
                        performed_by=request.user
                    )
                    messages.success(request, f'Hotel data for {date_str} updated successfully')
            except Exception as e:
                messages.error(request, f'Error updating hotel data: {str(e)}')
        
        elif action == 'edit_competitor_data':
            data_id = request.POST.get('competitor_data_id')
            date_str = request.POST.get('date')
            estimated_occupancy = request.POST.get('estimated_occupancy')
            estimated_average_rate = request.POST.get('estimated_average_rate')
            notes = request.POST.get('notes', '')
            
            try:
                comp_data = CompetitorData.objects.get(id=data_id)
                changes = {}
                
                if str(comp_data.date) != date_str:
                    changes['date'] = {'old': str(comp_data.date), 'new': date_str}
                if str(comp_data.estimated_occupancy) != estimated_occupancy:
                    changes['estimated_occupancy'] = {'old': str(comp_data.estimated_occupancy), 'new': estimated_occupancy}
                if str(comp_data.estimated_average_rate) != estimated_average_rate:
                    changes['estimated_average_rate'] = {'old': str(comp_data.estimated_average_rate), 'new': estimated_average_rate}
                if comp_data.notes != notes:
                    changes['notes'] = {'old': comp_data.notes, 'new': notes}
                
                if changes:
                    comp_data.date = date_str
                    comp_data.estimated_occupancy = estimated_occupancy
                    comp_data.estimated_average_rate = estimated_average_rate
                    comp_data.notes = notes
                    comp_data.save()
                    
                    # Calculate and update market performance indices
                    calculate_market_indices(date_str)
                    
                    AuditLog.objects.create(
                        entity_type='competitor_data',
                        entity_id=comp_data.id,
                        action='update',
                        changes=changes,
                        performed_by=request.user
                    )
                    messages.success(request, f'Competitor data for {date_str} updated successfully')
            except Exception as e:
                messages.error(request, f'Error updating competitor data: {str(e)}')
        
        elif action in ['delete_hotel_data', 'delete_competitor_data']:
            data_id = request.POST.get('data_id')
            try:
                if action == 'delete_hotel_data':
                    data = DailyData.objects.get(id=data_id)
                    entity_type = 'hotel_data'
                else:
                    data = CompetitorData.objects.get(id=data_id)
                    entity_type = 'competitor_data'
                
                date_str = str(data.date)
                data_dict = {
                    'date': str(data.date),
                    'notes': data.notes
                }
                
                if entity_type == 'hotel_data':
                    data_dict.update({
                        'rooms_sold': data.rooms_sold,
                        'total_revenue': str(data.total_revenue),
                        'occupancy_percentage': str(data.occupancy_percentage),
                        'average_rate': str(data.average_rate),
                        'revpar': str(data.revpar)
                    })
                else:
                    data_dict.update({
                        'competitor': data.competitor.name,
                        'estimated_occupancy': str(data.estimated_occupancy),
                        'estimated_average_rate': str(data.estimated_average_rate)
                    })
                
                data.delete()
                
                AuditLog.objects.create(
                    entity_type=entity_type,
                    entity_id=data_id,
                    action='delete',
                    changes={'deleted_data': data_dict},
                    performed_by=request.user
                )
                messages.success(request, f'Data for {date_str} deleted successfully')
            except Exception as e:
                messages.error(request, f'Error deleting data: {str(e)}')
    
    # Handle GET requests with filters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    data_type = request.GET.get('data_type', 'all')
    
    # Base querysets
    hotel_data = DailyData.objects.filter(hotel=hotel)
    competitor_data = CompetitorData.objects.all()
    
    # Apply date filters if provided
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
            hotel_data = hotel_data.filter(date__gte=start_date)
            competitor_data = competitor_data.filter(date__gte=start_date)
        except ValueError:
            messages.warning(request, 'Invalid start date format')
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
            hotel_data = hotel_data.filter(date__lte=end_date)
            competitor_data = competitor_data.filter(date__lte=end_date)
        except ValueError:
            messages.warning(request, 'Invalid end date format')
    
    # Apply data type filter
    if data_type == 'hotel':
        competitor_data = competitor_data.none()
    elif data_type == 'competitor':
        hotel_data = hotel_data.none()
    
    # Order by date
    hotel_data = hotel_data.order_by('-date')
    competitor_data = competitor_data.order_by('-date')
    
    context = {
        'title': 'Data Entry - Benchstay',
        'hotel': hotel,
        'competitors': competitors,
        'hotel_data': hotel_data[:50],  # Limit to most recent 50 entries
        'competitor_data': competitor_data[:50],  # Limit to most recent 50 entries
        'today': timezone.now().date().isoformat()
    }
    return render(request, 'hotel_management/data_entry.html', context)

@login_required
def hotel_data_api(request, pk):
    """API endpoint for retrieving hotel data"""
    if not (
        request.user.has_perm('accounts.view_hotel_management') or
        request.user.has_perm('accounts.view_data_entry')
    ):
        raise PermissionDenied
    try:
        data = get_object_or_404(DailyData, id=pk)
        return JsonResponse({
            'date': data.date.isoformat(),
            'rooms_sold': data.rooms_sold,
            'total_revenue': str(data.total_revenue),
            'notes': data.notes
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
def competitor_data_api(request, pk):
    """API endpoint for retrieving competitor data"""
    if not (
        request.user.has_perm('accounts.view_hotel_management') or
        request.user.has_perm('accounts.view_data_entry')
    ):
        raise PermissionDenied
    try:
        data = get_object_or_404(CompetitorData, id=pk)
        return JsonResponse({
            'date': data.date.isoformat(),
            'estimated_occupancy': str(data.estimated_occupancy),
            'estimated_average_rate': str(data.estimated_average_rate),
            'notes': data.notes
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@permission_required('accounts.view_hotel_management', raise_exception=True)
def daily_data(request):
    """View for managing daily hotel data"""
    hotel = Hotel.objects.first()
    
    # If no hotel exists yet, redirect to hotel data page
    if not hotel:
        messages.info(request, 'Please set up your hotel information first')
        return redirect('hotel_management:hotel_data')
    
    if request.method == 'POST':
        date_str = request.POST.get('date')
        rooms_sold = request.POST.get('rooms_sold')
        total_revenue = request.POST.get('total_revenue')
        notes = request.POST.get('notes', '')
        
        # Validate input
        if not all([date_str, rooms_sold, total_revenue]):
            messages.error(request, 'Please fill in all required fields')
        else:
            try:
                # Try to get existing data for this date or create new
                daily_data, created = DailyData.objects.get_or_create(
                    date=date_str,
                    hotel=hotel,
                    defaults={
                        'rooms_sold': rooms_sold,
                        'total_revenue': total_revenue,
                        'notes': notes,
                        'total_rooms': hotel.total_rooms
                    }
                )
                
                if not created:
                    # Update existing record
                    daily_data.rooms_sold = rooms_sold
                    daily_data.total_revenue = total_revenue
                    daily_data.notes = notes
                    daily_data.save()
                    messages.success(request, f'Data for {date_str} updated successfully')
                else:
                    messages.success(request, f'Data for {date_str} added successfully')
                    
            except Exception as e:
                messages.error(request, f'Error saving data: {str(e)}')
    
    # Get all daily data for display, ordered by most recent first
    all_data = DailyData.objects.filter(hotel=hotel).order_by('-date')
    
    context = {
        'title': 'Daily Data - Benchstay',
        'hotel': hotel,
        'all_data': all_data,
        'today': timezone.now().date().isoformat(),
    }
    return render(request, 'hotel_management/daily_data.html', context)



@login_required
@permission_required('accounts.view_hotel_management', raise_exception=True)
def hotel_competitor_management(request):
    """View for managing hotel and competitor information with audit logging"""
    hotel = Hotel.objects.first()
    competitors = Competitor.objects.all().order_by('name')
    audit_logs = AuditLog.objects.all().order_by('-performed_at')[:50]  # Get last 50 audit logs
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'delete_competitor':
            competitor_id = request.POST.get('competitor_id')
            delete_type = request.POST.get('delete_type', 'soft')
            
            try:
                competitor = Competitor.objects.get(id=competitor_id)
                if delete_type == 'soft':
                    competitor.is_active = False
                    competitor.status = 'inactive'
                    competitor.save()
                    
                    AuditLog.objects.create(
                        entity_type='competitor',
                        entity_id=competitor.id,
                        action='soft_delete',
                        changes={'status': {'old': 'active', 'new': 'inactive'}},
                        performed_by=request.user
                    )
                    messages.success(request, f'Competitor {competitor.name} has been deactivated')
                else:
                    # Hard delete - remove competitor and all associated data
                    competitor_name = competitor.name
                    CompetitorData.objects.filter(competitor=competitor).delete()
                    competitor.delete()
                    
                    AuditLog.objects.create(
                        entity_type='competitor',
                        entity_id=competitor_id,
                        action='hard_delete',
                        changes={'deleted': True},
                        performed_by=request.user
                    )
                    messages.success(request, f'Competitor {competitor_name} and all associated data have been permanently deleted')
            except Competitor.DoesNotExist:
                messages.error(request, 'Competitor not found')
            except Exception as e:
                messages.error(request, f'Error deleting competitor: {str(e)}')
        
        elif action == 'update_hotel':
            name = request.POST.get('name')
            address = request.POST.get('address')
            phone = request.POST.get('phone')
            email = request.POST.get('email')
            total_rooms = request.POST.get('total_rooms')
            logo = request.FILES.get('logo')
            
            if not all([name, address, phone, email, total_rooms]):
                messages.error(request, 'Please fill in all required fields')
            else:
                try:
                    changes = {}
                    if not hotel:
                        hotel = Hotel.objects.create(
                            name=name,
                            address=address,
                            phone=phone,
                            email=email,
                            total_rooms=total_rooms
                        )
                        if logo:
                            hotel.logo = logo
                            hotel.save()
                        
                        changes = {
                            'name': name,
                            'address': address,
                            'phone': phone,
                            'email': email,
                            'total_rooms': total_rooms
                        }
                        if logo:
                            changes['logo'] = 'Uploaded'
                            
                        AuditLog.objects.create(
                            entity_type='hotel',
                            entity_id=hotel.id,
                            action='create',
                            changes=changes,
                            performed_by=request.user
                        )
                        messages.success(request, 'Hotel information added successfully')
                    else:
                        # Track changes
                        if hotel.name != name:
                            changes['name'] = {'old': hotel.name, 'new': name}
                        if hotel.address != address:
                            changes['address'] = {'old': hotel.address, 'new': address}
                        if hotel.phone != phone:
                            changes['phone'] = {'old': hotel.phone, 'new': phone}
                        if hotel.email != email:
                            changes['email'] = {'old': hotel.email, 'new': email}
                        if hotel.total_rooms != int(total_rooms):
                            changes['total_rooms'] = {'old': hotel.total_rooms, 'new': int(total_rooms)}
                        if logo:
                            changes['logo'] = {'old': str(hotel.logo), 'new': 'Updated'}
                        
                        if changes or logo:
                            hotel.name = name
                            hotel.address = address
                            hotel.phone = phone
                            hotel.email = email
                            hotel.total_rooms = total_rooms
                            if logo:
                                hotel.logo = logo
                            hotel.save()
                            
                            AuditLog.objects.create(
                                entity_type='hotel',
                                entity_id=hotel.id,
                                action='update',
                                changes=changes,
                                performed_by=request.user
                            )
                            messages.success(request, 'Hotel information updated successfully')
                except Exception as e:
                    messages.error(request, f'Error saving hotel information: {str(e)}')
        
        elif action == 'add_competitor':
            name = request.POST.get('name')
            address = request.POST.get('address')
            total_rooms = request.POST.get('total_rooms')
            notes = request.POST.get('notes', '')
            
            if not all([name, address, total_rooms]):
                messages.error(request, 'Please fill in all required fields')
            else:
                try:
                    competitor = Competitor.objects.create(
                        name=name,
                        address=address,
                        total_rooms=total_rooms,
                        notes=notes,
                        is_active=True,
                        status='active'
                    )
                    
                    changes = {
                        'name': name,
                        'address': address,
                        'total_rooms': total_rooms,
                        'notes': notes
                    }
                    
                    AuditLog.objects.create(
                        entity_type='competitor',
                        entity_id=competitor.id,
                        action='create',
                        changes=changes,
                        performed_by=request.user
                    )
                    messages.success(request, f'Competitor {name} added successfully')
                except Exception as e:
                    messages.error(request, f'Error adding competitor: {str(e)}')
        
        elif action == 'update_competitor':
            competitor_id = request.POST.get('competitor_id')
            name = request.POST.get('name')
            address = request.POST.get('address')
            total_rooms = request.POST.get('total_rooms')
            notes = request.POST.get('notes', '')
            
            status = request.POST.get('status')
            if not all([competitor_id, name, address, total_rooms, status]):
                messages.error(request, 'Please fill in all required fields')
            else:
                try:
                    competitor = Competitor.objects.get(id=competitor_id)
                    changes = {}
                    
                    if competitor.name != name:
                        changes['name'] = {'old': competitor.name, 'new': name}
                    if competitor.address != address:
                        changes['address'] = {'old': competitor.address, 'new': address}
                    if competitor.total_rooms != int(total_rooms):
                        changes['total_rooms'] = {'old': competitor.total_rooms, 'new': int(total_rooms)}
                    if competitor.notes != notes:
                        changes['notes'] = {'old': competitor.notes, 'new': notes}
                    if competitor.status != status:
                        changes['status'] = {'old': competitor.status, 'new': status}
                        competitor.is_active = (status == 'active')
                    
                    if changes:
                        competitor.name = name
                        competitor.address = address
                        competitor.total_rooms = total_rooms
                        competitor.notes = notes
                        competitor.status = status
                        competitor.save()
                        
                        AuditLog.objects.create(
                            entity_type='competitor',
                            entity_id=competitor.id,
                            action='update',
                            changes=changes,
                            performed_by=request.user
                        )
                        messages.success(request, f'Competitor {name} updated successfully')
                except Competitor.DoesNotExist:
                    messages.error(request, 'Competitor not found')
                except Exception as e:
                    messages.error(request, f'Error updating competitor: {str(e)}')
        else:
            try:
                if hotel:
                    # Update existing hotel
                    hotel.name = name
                    hotel.address = address
                    hotel.phone = phone
                    hotel.email = email
                    hotel.total_rooms = total_rooms
                    hotel.save()
                    messages.success(request, 'Hotel information updated successfully')
                else:
                    # Create new hotel
                    Hotel.objects.create(
                        name=name,
                        address=address,
                        phone=phone,
                        email=email,
                        total_rooms=total_rooms
                    )
                    messages.success(request, 'Hotel information saved successfully')
            except Exception as e:
                messages.error(request, f'Error saving hotel information: {str(e)}')
    
    context = {
        'title': 'Hotel & Competitor Management - Benchstay',
        'hotel': hotel,
        'competitors': competitors,
        'audit_logs': audit_logs
    }
    return render(request, 'hotel_management/hotel_competitor_management.html', context)
