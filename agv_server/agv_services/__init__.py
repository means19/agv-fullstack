"""
AGV Services Package

This package contains services for the SSI-DMAS-ET auction system:
- auctioneer_service: Calculate baseline costs for tasks (Algorithm A)
- bidding_service: Calculate AGV bids with dynamic normalization (Algorithm B)
- task_manager: Coordinate auction process and task assignment

Reference: docs/auction-logic/auction-logic-implementation-guide.md
"""

from .auctioneer_service import auctioneer_service, AuctioneerService
from .bidding_service import BiddingService
from .task_manager import task_manager, TaskManager

__all__ = [
    'auctioneer_service',
    'AuctioneerService',
    'BiddingService',
    'task_manager',
    'TaskManager',
]
