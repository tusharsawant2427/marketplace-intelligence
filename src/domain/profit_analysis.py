from dataclasses import dataclass

@dataclass
class ProfitAnalysis:
    
    """ 
     Profit Analysis
    """
    gross_profit: float
    profit_percentage: float
    profit_per_item: float
    break_even_price: float