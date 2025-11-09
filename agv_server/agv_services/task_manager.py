"""
Task Manager - Auction Coordination Service

This service coordinates the SSI-DMAS-ET auction process:
1. Receives new orders
2. Calculates baseline using AuctioneerService
3. Broadcasts task to all AGVs
4. Collects bids from AGVs using BiddingService
5. Selects winner and assigns task

Reference: docs/auction-logic/auction-logic-implementation-guide.md - Section 5
"""

from typing import Dict, Optional, Tuple
import sys
import os
from datetime import datetime, timezone

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from .auctioneer_service import auctioneer_service
from .bidding_service import BiddingService
from agv_data.models import Agv


class TaskManager:
    """
    Manages the auction process for task assignment.
    
    Workflow:
        1. New order arrives
        2. Auctioneer calculates baseline (E_baseline, TFT_baseline)
        3. Broadcast baseline to all active AGVs
        4. Each AGV calculates bid using BiddingService
        5. Winner selected (lowest bid)
        6. Winner AGV runs Intention Ant (book_slot_strict)
    """
    
    def __init__(self):
        self.bidding_service = BiddingService()
    
    def run_auction(self, order) -> Optional[Tuple[int, float]]:
        """
        Run complete auction process for a new order.
        
        Args:
            order: Order object from order_data.models
            
        Returns:
            Optional[Tuple[int, float]]: (winner_agv_id, winning_bid) or None if auction fails
            
        Process:
            1. Calculate baseline costs
            2. Get all idle AGVs
            3. Collect bids from each AGV
            4. Select winner (minimum bid)
            5. Return winner info (actual task assignment done elsewhere)
        """
        print(f"\n{'='*80}")
        print(f"STARTING AUCTION FOR ORDER {order.order_id}")
        print(f"{'='*80}")
        print(f"Parking: {order.parking_node}")
        print(f"Storage (Pickup): {order.storage_node}")
        print(f"Workstation (Delivery): {order.workstation_node}")
        print(f"Start Time: {order.start_time}")
        
        # Step 1: Auctioneer calculates baseline
        print(f"\n[Step 1] Auctioneer calculating baseline...")
        E_baseline, TFT_baseline = auctioneer_service.calculate_baseline(order)
        
        if E_baseline == float('inf') or TFT_baseline == float('inf'):
            print(f"[ERROR] Cannot calculate baseline for Order {order.order_id}")
            print(f"Order is not feasible (no valid path exists)")
            return None
        
        print(f"✓ Baseline calculated successfully")
        
        # Step 2: Get all AGVs (both idle and busy can bid)
        print(f"\n[Step 2] Finding available AGVs...")
        all_agvs = Agv.objects.all()
        
        if not all_agvs.exists():
            print(f"[ERROR] No AGVs available for auction")
            return None
        
        idle_count = all_agvs.filter(motion_state=Agv.IDLE).count()
        busy_count = all_agvs.count() - idle_count
        
        print(f"✓ Found {all_agvs.count()} AGVs (Idle: {idle_count}, Busy: {busy_count})")
        
        # Step 3: Collect bids from all AGVs
        print(f"\n[Step 3] Collecting bids from AGVs...")
        bids: Dict[int, float] = {}
        
        for agv in all_agvs:
            print(f"\n--- AGV {agv.agv_id} ---")
            try:
                bid = self.bidding_service.calculate_bid_for_agv(
                    agv=agv,
                    order=order,
                    E_baseline=E_baseline,
                    TFT_baseline=TFT_baseline
                )
                
                if bid != float('inf'):
                    bids[agv.agv_id] = bid
                    print(f"✓ AGV {agv.agv_id} bid: {bid:.6f}")
                else:
                    print(f"✗ AGV {agv.agv_id} cannot fulfill order (bid = inf)")
                    
            except Exception as e:
                print(f"✗ AGV {agv.agv_id} bidding failed: {e}")
                import traceback
                traceback.print_exc()
        
        if not bids:
            print(f"\n[ERROR] No valid bids received for Order {order.order_id}")
            return None
        
        # Step 4: Select winner (minimum bid)
        print(f"\n[Step 4] Selecting auction winner...")
        winner_agv_id = min(bids, key=bids.get)
        winning_bid = bids[winner_agv_id]
        
        print(f"\n{'='*80}")
        print(f"AUCTION COMPLETED")
        print(f"{'='*80}")
        print(f"Winner: AGV {winner_agv_id}")
        print(f"Winning Bid: {winning_bid:.6f}")
        print(f"Total Bidders: {len(bids)}")
        print(f"\nAll Bids:")
        for agv_id, bid in sorted(bids.items(), key=lambda x: x[1]):
            marker = "★ WINNER" if agv_id == winner_agv_id else ""
            print(f"  AGV {agv_id}: {bid:.6f} {marker}")
        print(f"{'='*80}\n")
        
        return (winner_agv_id, winning_bid)
    
    def assign_task_to_winner(self, order, winner_agv_id: int) -> bool:
        """
        Assign the task to the winning AGV.
        
        Args:
            order: Order object
            winner_agv_id: ID of the winning AGV
            
        Returns:
            bool: True if assignment successful, False otherwise
            
        Note:
            This triggers the Intention Ant logic:
            - AGV creates optimal route plan
            - AGV calls book_slot_strict for each resource
            - If any booking fails (409 conflict), AGV returns to idle
        """
        try:
            winner_agv = Agv.objects.get(agv_id=winner_agv_id)
            
            print(f"\n[TaskManager] Assigning Order {order.order_id} to AGV {winner_agv_id}")
            
            # TODO: Implement task assignment logic
            # This should:
            # 1. Update AGV state
            # 2. Create initial route plan
            # 3. Trigger Intention Ant (book_slot_strict calls)
            # 4. Handle booking failures (409 -> return to idle)
            
            # For now, just log
            print(f"[TODO] Implement Intention Ant logic for task assignment")
            print(f"       AGV {winner_agv_id} should now book resources and start execution")
            
            return True
            
        except Agv.DoesNotExist:
            print(f"[ERROR] Winner AGV {winner_agv_id} not found in database")
            return False
        except Exception as e:
            print(f"[ERROR] Task assignment failed: {e}")
            import traceback
            traceback.print_exc()
            return False


# Singleton instance
task_manager = TaskManager()


if __name__ == "__main__":
    # Test the auction process
    from order_data.models import Order
    from datetime import time, date
    
    print("="*80)
    print("TASK MANAGER - AUCTION TEST")
    print("="*80)
    print("\nNote: This requires:")
    print("  1. Django server running")
    print("  2. Database with ResourceAgent nodes (map data)")
    print("  3. At least one idle AGV")
    print("  4. Sample Order in database")
    print("\nAttempting to run test auction...")
    
    try:
        # Try to get first order
        test_order = Order.objects.first()
        
        if test_order is None:
            print("\n[ERROR] No orders found in database")
            print("Please create a test order first.")
        else:
            print(f"\n[INFO] Found test order: {test_order}")
            
            # Run auction
            result = task_manager.run_auction(test_order)
            
            if result:
                winner_id, winning_bid = result
                print(f"\n[SUCCESS] Auction completed")
                print(f"Next step: Assign task to AGV {winner_id}")
            else:
                print(f"\n[FAILURE] Auction failed")
                
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "="*80)
