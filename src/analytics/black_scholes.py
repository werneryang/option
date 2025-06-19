import numpy as np
import pandas as pd
from scipy.stats import norm
from scipy.optimize import brentq
from dataclasses import dataclass
from typing import Union, Optional
from datetime import date, datetime
import math

@dataclass
class OptionParams:
    """Parameters for option pricing calculations"""
    S: float  # Current stock price
    K: float  # Strike price
    T: float  # Time to expiration (in years)
    r: float  # Risk-free rate
    sigma: float  # Volatility (annualized)
    option_type: str  # 'call' or 'put'
    q: float = 0.0  # Dividend yield

@dataclass
class OptionPrice:
    """Result of option pricing calculation"""
    price: float
    delta: float
    gamma: float
    theta: float
    vega: float
    rho: float
    params: OptionParams

class BlackScholesCalculator:
    """
    Black-Scholes option pricing model implementation with Greeks calculation
    """
    
    @staticmethod
    def _d1(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate d1 parameter for Black-Scholes formula"""
        if T <= 0 or sigma <= 0:
            return 0.0
        return (np.log(S / K) + (r - q + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    
    @staticmethod
    def _d2(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate d2 parameter for Black-Scholes formula"""
        if T <= 0 or sigma <= 0:
            return 0.0
        d1 = BlackScholesCalculator._d1(S, K, T, r, sigma, q)
        return d1 - sigma * np.sqrt(T)
    
    @staticmethod
    def option_price(S: float, K: float, T: float, r: float, sigma: float, 
                    option_type: str, q: float = 0.0) -> float:
        """
        Calculate Black-Scholes option price
        
        Args:
            S: Current stock price
            K: Strike price
            T: Time to expiration (years)
            r: Risk-free rate (annual)
            sigma: Volatility (annual)
            option_type: 'call' or 'put'
            q: Dividend yield (annual)
            
        Returns:
            Option price
        """
        if T <= 0:
            if option_type.lower() == 'call':
                return max(S - K, 0)
            else:
                return max(K - S, 0)
        
        if sigma <= 0:
            return 0.0
            
        d1 = BlackScholesCalculator._d1(S, K, T, r, sigma, q)
        d2 = BlackScholesCalculator._d2(S, K, T, r, sigma, q)
        
        if option_type.lower() == 'call':
            price = S * np.exp(-q * T) * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)
        elif option_type.lower() == 'put':
            price = K * np.exp(-r * T) * norm.cdf(-d2) - S * np.exp(-q * T) * norm.cdf(-d1)
        else:
            raise ValueError(f"Invalid option_type: {option_type}. Must be 'call' or 'put'")
        
        return max(price, 0.0)
    
    @staticmethod
    def delta(S: float, K: float, T: float, r: float, sigma: float, 
             option_type: str, q: float = 0.0) -> float:
        """Calculate option delta (price sensitivity to underlying price)"""
        if T <= 0 or sigma <= 0:
            if option_type.lower() == 'call':
                return 1.0 if S > K else 0.0
            else:
                return -1.0 if S < K else 0.0
        
        d1 = BlackScholesCalculator._d1(S, K, T, r, sigma, q)
        
        if option_type.lower() == 'call':
            return np.exp(-q * T) * norm.cdf(d1)
        elif option_type.lower() == 'put':
            return -np.exp(-q * T) * norm.cdf(-d1)
        else:
            raise ValueError(f"Invalid option_type: {option_type}")
    
    @staticmethod
    def gamma(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate option gamma (delta sensitivity to underlying price)"""
        if T <= 0 or sigma <= 0:
            return 0.0
        
        d1 = BlackScholesCalculator._d1(S, K, T, r, sigma, q)
        return np.exp(-q * T) * norm.pdf(d1) / (S * sigma * np.sqrt(T))
    
    @staticmethod
    def theta(S: float, K: float, T: float, r: float, sigma: float, 
             option_type: str, q: float = 0.0) -> float:
        """Calculate option theta (time decay) - per day"""
        if T <= 0:
            return 0.0
        
        if sigma <= 0:
            return 0.0
        
        d1 = BlackScholesCalculator._d1(S, K, T, r, sigma, q)
        d2 = BlackScholesCalculator._d2(S, K, T, r, sigma, q)
        
        term1 = -S * np.exp(-q * T) * norm.pdf(d1) * sigma / (2 * np.sqrt(T))
        
        if option_type.lower() == 'call':
            term2 = -r * K * np.exp(-r * T) * norm.cdf(d2)
            term3 = q * S * np.exp(-q * T) * norm.cdf(d1)
        elif option_type.lower() == 'put':
            term2 = r * K * np.exp(-r * T) * norm.cdf(-d2)
            term3 = -q * S * np.exp(-q * T) * norm.cdf(-d1)
        else:
            raise ValueError(f"Invalid option_type: {option_type}")
        
        theta_annual = term1 + term2 + term3
        return theta_annual / 365.0  # Convert to per-day
    
    @staticmethod
    def vega(S: float, K: float, T: float, r: float, sigma: float, q: float = 0.0) -> float:
        """Calculate option vega (volatility sensitivity) - per 1% vol change"""
        if T <= 0 or sigma <= 0:
            return 0.0
        
        d1 = BlackScholesCalculator._d1(S, K, T, r, sigma, q)
        return S * np.exp(-q * T) * norm.pdf(d1) * np.sqrt(T) / 100.0
    
    @staticmethod
    def rho(S: float, K: float, T: float, r: float, sigma: float, 
           option_type: str, q: float = 0.0) -> float:
        """Calculate option rho (interest rate sensitivity) - per 1% rate change"""
        if T <= 0 or sigma <= 0:
            return 0.0
        
        d2 = BlackScholesCalculator._d2(S, K, T, r, sigma, q)
        
        if option_type.lower() == 'call':
            return K * T * np.exp(-r * T) * norm.cdf(d2) / 100.0
        elif option_type.lower() == 'put':
            return -K * T * np.exp(-r * T) * norm.cdf(-d2) / 100.0
        else:
            raise ValueError(f"Invalid option_type: {option_type}")
    
    @classmethod
    def calculate_option(cls, params: OptionParams) -> OptionPrice:
        """
        Calculate option price and all Greeks
        
        Args:
            params: OptionParams object with all required parameters
            
        Returns:
            OptionPrice object with price and Greeks
        """
        price = cls.option_price(
            params.S, params.K, params.T, params.r, params.sigma, 
            params.option_type, params.q
        )
        
        delta = cls.delta(
            params.S, params.K, params.T, params.r, params.sigma, 
            params.option_type, params.q
        )
        
        gamma = cls.gamma(
            params.S, params.K, params.T, params.r, params.sigma, params.q
        )
        
        theta = cls.theta(
            params.S, params.K, params.T, params.r, params.sigma, 
            params.option_type, params.q
        )
        
        vega = cls.vega(
            params.S, params.K, params.T, params.r, params.sigma, params.q
        )
        
        rho = cls.rho(
            params.S, params.K, params.T, params.r, params.sigma, 
            params.option_type, params.q
        )
        
        return OptionPrice(
            price=price,
            delta=delta,
            gamma=gamma,
            theta=theta,
            vega=vega,
            rho=rho,
            params=params
        )
    
    @staticmethod
    def implied_volatility(market_price: float, S: float, K: float, T: float, 
                          r: float, option_type: str, q: float = 0.0) -> Optional[float]:
        """
        Calculate implied volatility using Brent's method
        
        Args:
            market_price: Observed market price of the option
            S: Current stock price
            K: Strike price
            T: Time to expiration (years)
            r: Risk-free rate
            option_type: 'call' or 'put'
            q: Dividend yield
            
        Returns:
            Implied volatility (annual) or None if not found
        """
        if T <= 0 or market_price <= 0:
            return None
        
        # Check intrinsic value bounds
        if option_type.lower() == 'call':
            intrinsic = max(S - K, 0)
        else:
            intrinsic = max(K - S, 0)
        
        if market_price < intrinsic:
            return None
        
        def objective(sigma):
            try:
                theoretical_price = BlackScholesCalculator.option_price(
                    S, K, T, r, sigma, option_type, q
                )
                return theoretical_price - market_price
            except:
                return float('inf')
        
        try:
            # Use Brent's method to find volatility between 0.1% and 500%
            iv = brentq(objective, 0.001, 5.0, maxiter=100)
            return iv if 0.001 <= iv <= 5.0 else None
        except (ValueError, RuntimeError):
            return None
    
    @staticmethod
    def time_to_expiration(expiration_date: Union[date, datetime, str], 
                          current_date: Optional[Union[date, datetime]] = None) -> float:
        """
        Calculate time to expiration in years
        
        Args:
            expiration_date: Option expiration date
            current_date: Current date (defaults to today)
            
        Returns:
            Time to expiration in years
        """
        if current_date is None:
            current_date = datetime.now().date()
        
        if isinstance(current_date, datetime):
            current_date = current_date.date()
        
        if isinstance(expiration_date, str):
            expiration_date = datetime.strptime(expiration_date, '%Y-%m-%d').date()
        elif isinstance(expiration_date, datetime):
            expiration_date = expiration_date.date()
        
        days_to_expiry = (expiration_date - current_date).days
        return max(days_to_expiry / 365.0, 0.0)

# Convenience functions for easy use
def black_scholes_price(S: float, K: float, T: float, r: float, sigma: float, 
                       option_type: str, q: float = 0.0) -> float:
    """Quick Black-Scholes price calculation"""
    return BlackScholesCalculator.option_price(S, K, T, r, sigma, option_type, q)

def calculate_greeks(S: float, K: float, T: float, r: float, sigma: float, 
                    option_type: str, q: float = 0.0) -> dict:
    """Calculate all Greeks and return as dictionary"""
    calc = BlackScholesCalculator
    return {
        'price': calc.option_price(S, K, T, r, sigma, option_type, q),
        'delta': calc.delta(S, K, T, r, sigma, option_type, q),
        'gamma': calc.gamma(S, K, T, r, sigma, q),
        'theta': calc.theta(S, K, T, r, sigma, option_type, q),
        'vega': calc.vega(S, K, T, r, sigma, q),
        'rho': calc.rho(S, K, T, r, sigma, option_type, q)
    }