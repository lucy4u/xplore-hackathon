class CarbonCalculator:
    # Emission factors (kg CO2 per passenger-kilometer)
    EMISSION_FACTORS = {
        'bus': 0.1,     # Average city bus
        'train': 0.04,  # Electric/hybrid train
        'metro': 0.05,  # Urban metro system
        'auto': 0.2     # Auto-rickshaw
    }
    
    @classmethod
    def calculate_carbon_footprint(cls, transport_mode, distance):
        """
        Calculate carbon footprint for a single journey
        """
        emission_factor = cls.EMISSION_FACTORS.get(transport_mode, 0)
        daily_emissions = distance * emission_factor
        annual_emissions = daily_emissions * 365
        
        # Calculate emissions saved compared to private vehicle
        private_car_factor = 0.192  # kg CO2 per passenger-km
        emissions_saved = max(0, (private_car_factor - emission_factor) * distance)
        annual_savings = emissions_saved * 365
        
        return {
            'daily_emissions': round(daily_emissions, 2),
            'annual_emissions': round(annual_emissions, 2),
            'emissions_saved': round(emissions_saved, 2),
            'annual_savings': round(annual_savings, 2)
        }

class RewardCalculator:
    @staticmethod
    def calculate_points(emissions_saved):
        """
        Convert emissions saved to reward points
        """
        return int(emissions_saved * 10)
    
    @staticmethod
    def get_reward_tier(total_points):
        """
        Determine reward tier based on total points
        """
        if total_points < 100:
            return "Green Starter"
        elif total_points < 500:
            return "Eco Warrior"
        elif total_points < 1000:
            return "Climate Champion"
        else:
            return "Sustainability Hero"