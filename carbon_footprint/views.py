from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import CarbonFootprintEntry, UserRewardProfile
from .utils import CarbonCalculator, RewardCalculator

@login_required
@csrf_exempt
def log_transport(request):
    if request.method == 'POST':
        try:
            # Extract form data
            transport_mode = request.POST.get('transport_mode')
            distance = float(request.POST.get('distance'))
            
            # Calculate carbon footprint
            carbon_data = CarbonCalculator.calculate_carbon_footprint(
                transport_mode, 
                distance
            )
            
            # Create carbon footprint entry
            entry = CarbonFootprintEntry.objects.create(
                user=request.user,
                transport_mode=transport_mode,
                distance=distance,
                daily_emissions=carbon_data['daily_emissions'],
                annual_emissions_equivalent=carbon_data['annual_emissions']
            )
            
            # Update or create user reward profile
            reward_profile, created = UserRewardProfile.objects.get_or_create(
                user=request.user
            )
            
            # Calculate reward points
            points_earned = RewardCalculator.calculate_points(
                carbon_data['emissions_saved']
            )
            reward_profile.total_points += points_earned
            reward_profile.total_emissions_saved += carbon_data['emissions_saved']
            reward_profile.save()
            
            return JsonResponse({
                'success': True,
                'carbon_data': carbon_data,
                'points_earned': points_earned,
                'total_points': reward_profile.total_points,
                'reward_tier': reward_profile.get_reward_tier()
            })
        
        except Exception as e:
            return JsonResponse({
                'success': False, 
                'error': str(e)
            }, status=400)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
def dashboard(request):
    """
    User dashboard to show carbon footprint history and rewards
    """
    entries = CarbonFootprintEntry.objects.filter(user=request.user)
    reward_profile, _ = UserRewardProfile.objects.get_or_create(user=request.user)
    
    context = {
        'entries': entries,
        'total_points': reward_profile.total_points,
        'reward_tier': reward_profile.get_reward_tier(),
        'total_emissions_saved': round(reward_profile.total_emissions_saved, 2)
    }
    
    return render(request, 'carbon_footprint/dashboard.html', context)