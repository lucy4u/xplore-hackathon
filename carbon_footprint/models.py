

# Create your models here.
from django.db import models
from django.contrib.auth.models import User

class TransportMode(models.TextChoices):
    BUS = 'bus', 'Bus'
    TRAIN = 'train', 'Train'
    METRO = 'metro', 'Metro'
    AUTO = 'auto', 'Auto-Rickshaw'

class CarbonFootprintEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    transport_mode = models.CharField(
        max_length=10, 
        choices=TransportMode.choices
    )
    distance = models.FloatField()  # kilometers
    travel_date = models.DateField(auto_now_add=True)
    
    # Emission calculations
    daily_emissions = models.FloatField(default=0)
    annual_emissions_equivalent = models.FloatField(default=0)

class UserRewardProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    total_points = models.IntegerField(default=0)
    total_emissions_saved = models.FloatField(default=0)
    
    def get_reward_tier(self):
        if self.total_points < 100:
            return "Green Starter"
        elif self.total_points < 500:
            return "Eco Warrior"
        elif self.total_points < 1000:
            return "Climate Champion"
        else:
            return "Sustainability Hero"