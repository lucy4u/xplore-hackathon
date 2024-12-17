from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import UserRegistrationForm, UserLoginForm
from .utils import CarbonCalculator, RewardCalculator
from .models import TransportMode, CarbonFootprintEntry, UserRewardProfile

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Create reward profile for new user
            UserRewardProfile.objects.create(user=user)
            
            # Log the user in
            username = form.cleaned_data.get('username')
            raw_password = form.cleaned_data.get('password1')
            user = authenticate(username=username, password=raw_password)
            login(request, user)
            
            messages.success(request, 'Registration successful!')
            return redirect('carbon_footprint:dashboard')
    else:
        form = UserRegistrationForm()
    return render(request, 'carbon_footprint/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, f'Welcome back, {username}!')
                return redirect('carbon_footprint:dashboard')
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Invalid username or password.')
    else:
        form = UserLoginForm()
    return render(request, 'carbon_footprint/login.html', {'form': form})
def dashboard(request):
    # Get transport modes for the dropdown
    transport_modes = TransportMode.choices
    
    # Retrieve or create user reward profile
    reward_profile, created = UserRewardProfile.objects.get_or_create(user=request.user)
    
    # Get user's carbon footprint entries
    entries = CarbonFootprintEntry.objects.filter(user=request.user).order_by('-travel_date')
    
    # Initialize context 
    context = {
        'transport_modes': transport_modes,
        'result': None,
        'reward_profile': reward_profile,
        'entries': entries,
    }
    
    # Handle form submission
    if request.method == 'POST':
        try:
            # Get form data
            distance = float(request.POST.get('distance'))
            transport_mode = request.POST.get('transport_mode')
            
            # Calculate carbon footprint
            result = CarbonCalculator.calculate_carbon_footprint(transport_mode, distance)
            
            # Create carbon footprint entry
            entry = CarbonFootprintEntry.objects.create(
                user=request.user,
                transport_mode=transport_mode,
                distance=distance,
                daily_emissions=result['daily_emissions'],
                annual_emissions_equivalent=result['annual_emissions']
            )
            
            # Calculate and update reward points
            points_earned = RewardCalculator.calculate_points(result['emissions_saved'])
            reward_profile.total_points += points_earned
            reward_profile.total_emissions_saved += result['emissions_saved']
            reward_profile.save()
            
            # Add additional context
            context['result'] = result
            context['transport_mode'] = transport_mode
            context['distance'] = distance
            context['points_earned'] = points_earned
            context['entries'] = CarbonFootprintEntry.objects.filter(user=request.user).order_by('-travel_date')
            context['reward_profile'] = reward_profile
        
        except Exception as e:
            context['error'] = str(e)
    
    return render(request, 'carbon_footprint/dashboard.html', context)