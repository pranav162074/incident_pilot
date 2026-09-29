import os
from hindsight_client import HindsightMemoryManager

def test_hindsight_workflow():
    print("=== Testing IncidentPilot Hindsight Memory Integration ===")
    mem_mgr = HindsightMemoryManager()
    
    # 1. Retain Memory
    print("[1] Testing Memory Retain...")
    success = mem_mgr.retain_incident_memory(
        incident_id="INC-9901",
        summary="High CPU usage on payment processing worker",
        root_cause="Infinite loop in retry queue logic when third-party API returned 429 Rate Limit",
        fix_applied="Added exponential backoff and max retry count of 3 in queue consumer",
        tags=["payment", "cpu", "queue"]
    )
    print(f"Retain status: {success}")
    
    # 2. Recall Memory
    print("[2] Testing Memory Recall...")
    results = mem_mgr.recall_context("Payment processing service stuck at 100% CPU on 429 errors")
    print(f"Retrieved {len(results)} relevant memories:")
    for r in results:
        print(f"- {r.get('content')[:100]}...")

if __name__ == "__main__":
    test_hindsight_workflow()