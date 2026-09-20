"""
scripts/benchmark.py — SIH Multi-Agent vs Fixed Signal Benchmark
================================================================
Runs a side-by-side comparative simulation:
  1. Baseline: Fixed-Time Traffic Signals (30s EW / 30s NS cycles)
  2. Proposed: Distributed Multi-Agent Adaptive Control (Rule-Based Coordination)

Outputs a comprehensive performance table measuring:
  - Average Vehicle Travel Time (seconds)
  - Maximum & Average Queue Length
  - Network Throughput (vehicles cleared)
  - Congestion Mitigation Improvement (%)
"""

import os
import sys
import cityflow

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import MultiAgentCoordinator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(BASE_DIR)

SIM_STEPS = 300


def run_fixed_signal_benchmark():
    """Simulate fixed-time signal cycles (30s EW, 30s NS)."""
    eng = cityflow.Engine("config_5j.json", thread_num=1)
    
    total_waiting_samples = []
    max_queue = 0

    for step in range(SIM_STEPS):
        # 30-second fixed phase alternation
        phase = 0 if (step // 30) % 2 == 0 else 1
        for jid in ["J1", "J2", "J3", "J4", "J5"]:
            eng.set_tl_phase(jid, phase)

        eng.next_step()

        lw = eng.get_lane_waiting_vehicle_count()
        total_w = sum(lw.values())
        total_waiting_samples.append(total_w)
        if total_w > max_queue:
            max_queue = total_w

    avg_wait = sum(total_waiting_samples) / len(total_waiting_samples)
    avg_travel = eng.get_average_travel_time()
    total_veh = eng.get_vehicle_count()

    return {
        "mode": "Fixed-Time Signal",
        "avg_travel_time": round(avg_travel, 2),
        "avg_waiting_vehicles": round(avg_wait, 2),
        "max_queue_vehicles": max_queue,
        "active_vehicles": total_veh
    }


def run_multi_agent_benchmark():
    """Simulate proposed Distributed Multi-Agent Adaptive Control."""
    eng = cityflow.Engine("config_5j.json", thread_num=1)
    coord = MultiAgentCoordinator(eng)

    total_waiting_samples = []
    max_queue = 0

    for step in range(SIM_STEPS):
        eng.next_step()

        veh_ids = eng.get_vehicles(include_waiting=True)
        v_map = {}
        for vid in veh_ids:
            try:
                v_map[vid] = eng.get_vehicle_info(vid)
            except Exception:
                pass

        if step % 3 == 0:
            coord.step(v_map)

        lw = eng.get_lane_waiting_vehicle_count()
        total_w = sum(lw.values())
        total_waiting_samples.append(total_w)
        if total_w > max_queue:
            max_queue = total_w

    avg_wait = sum(total_waiting_samples) / len(total_waiting_samples)
    avg_travel = eng.get_average_travel_time()
    total_veh = eng.get_vehicle_count()

    return {
        "mode": "Multi-Agent Adaptive AI",
        "avg_travel_time": round(avg_travel, 2),
        "avg_waiting_vehicles": round(avg_wait, 2),
        "max_queue_vehicles": max_queue,
        "active_vehicles": total_veh
    }


if __name__ == "__main__":
    print("\n" + "=" * 65)
    print("  🚦  SIH 2026 TRAFFIC MOBILITY BENCHMARK COMPARISON")
    print(f"  Simulation Horizon: {SIM_STEPS} Steps (~5 Minutes Real-Time)")
    print("=" * 65)

    print("\n[1/2] Running Fixed-Time Baseline Simulation...")
    fixed_res = run_fixed_signal_benchmark()

    print("[2/2] Running Multi-Agent Distributed AI Simulation...")
    ai_res = run_multi_agent_benchmark()

    # Calculate improvements
    travel_imprv = round((fixed_res["avg_travel_time"] - ai_res["avg_travel_time"]) / max(1, fixed_res["avg_travel_time"]) * 100, 1)
    wait_imprv = round((fixed_res["avg_waiting_vehicles"] - ai_res["avg_waiting_vehicles"]) / max(1, fixed_res["avg_waiting_vehicles"]) * 100, 1)
    queue_imprv = round((fixed_res["max_queue_vehicles"] - ai_res["max_queue_vehicles"]) / max(1, fixed_res["max_queue_vehicles"]) * 100, 1)

    print("\n" + "-" * 65)
    print(f"{'Performance Metric':<28} | {'Fixed-Time':<15} | {'Multi-Agent AI':<15}")
    print("-" * 65)
    print(f"{'Avg Travel Time (seconds)':<28} | {fixed_res['avg_travel_time']:<15} | {ai_res['avg_travel_time']:<15}")
    print(f"{'Avg Waiting Vehicles':<28} | {fixed_res['avg_waiting_vehicles']:<15} | {ai_res['avg_waiting_vehicles']:<15}")
    print(f"{'Max Queue Peak':<28} | {fixed_res['max_queue_vehicles']:<15} | {ai_res['max_queue_vehicles']:<15}")
    print(f"{'Active In-Transit Cars':<28} | {fixed_res['active_vehicles']:<15} | {ai_res['active_vehicles']:<15}")
    print("-" * 65)
    print(f"\n📊 SUMMARY OF AI IMPROVEMENTS:")
    print(f"  🚀 Travel Delay Reduction : {travel_imprv}%")
    print(f"  ⚡ Queue Length Reduction : {wait_imprv}%")
    print(f"  🛑 Peak Bottleneck Relief : {queue_imprv}%\n")
