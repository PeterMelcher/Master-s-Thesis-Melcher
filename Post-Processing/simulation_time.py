import sys
import os
import re
import csv

def analyze_log(case_dir, plot_time, plot_type, abs_limits=None):
    case_name = os.path.basename(os.path.normpath(case_dir))
    
    log_path = os.path.join(case_dir, "log.interFoam")
    if not os.path.exists(log_path):
        log_path = os.path.join(case_dir, "interFoamV10Cast.txt")
        
    if not os.path.exists(log_path):
        print(f"Error: Could not find log file at {log_path}")
        return

    last_time = 0.0
    last_clock_time = None
    last_execution_time = None
    num_cores = None
    
    # Tracking variables
    prev_time = None
    prev_clock = None
    
    sim_times = []
    comp_times = []

    # Regex patterns
    nprocs_pattern = re.compile(r"nProcs\s*:\s*(\d+)")
    time_pattern = re.compile(r"^Time = ([\d\.eE\+\-]+)")
    exec_pattern = re.compile(r"^ExecutionTime = ([\d\.eE\+\-]+) s\s+ClockTime = ([\d\.eE\+\-]+) s")

    if not plot_time:
        mode_text = "CSV appending"
    else:
        mode_text = f"{plot_type.upper()} plot generation"
        if abs_limits:
            mode_text += f" (Absolute Y-Axis: {abs_limits[0]} to {abs_limits[1]})"
            
    print(f"Parsing log for '{case_name}'... Mode: {mode_text}.")

    try:
        with open(log_path, 'r') as f:
            current_time = None
            for line in f:
                if num_cores is None:
                    nprocs_match = nprocs_pattern.search(line)
                    if nprocs_match:
                        num_cores = int(nprocs_match.group(1))
                        print(f"Detected {num_cores} cores from log file.")
                        
                time_match = time_pattern.match(line)
                if time_match:
                    current_time = float(time_match.group(1))
                    last_time = current_time
                
                exec_match = exec_pattern.search(line)
                if exec_match and current_time is not None:
                    last_execution_time = float(exec_match.group(1))
                    last_clock_time = float(exec_match.group(2))
                    
                    if plot_time and current_time > 0 and num_cores is not None:
                        if plot_type == "diff":
                            if prev_time is not None and prev_clock is not None:
                                delta_sim = current_time - prev_time
                                delta_clock = last_clock_time - prev_clock
                                
                                if delta_sim > 0 and delta_clock > 0:
                                    diff_cost = (delta_clock / 3600.0 * num_cores) / delta_sim
                                    sim_times.append(current_time)
                                    comp_times.append(diff_cost)
                        else:
                            # Default to Cumulative
                            cum_cost = (last_clock_time / 3600.0 * num_cores) / current_time
                            sim_times.append(current_time)
                            comp_times.append(cum_cost)
                            
                    # Update previous states
                    prev_time = current_time
                    prev_clock = last_clock_time
                        
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    if num_cores is None:
        print("Warning: 'nProcs' not found in log header. Defaulting to 1 core.")
        num_cores = 1

    if last_time > 0 and last_clock_time is not None:
        clock_hours = last_clock_time / 3600.0
        final_cumulative_cost = (clock_hours * num_cores) / last_time
        
        print(f"--- Simulation Time Analysis for '{case_name}' ---")
        print(f"Cores Detected      : {num_cores}")
        print(f"Last Simulated Time : {last_time:.6g} s")
        print(f"Last Clock Time     : {last_clock_time:.2f} s ({clock_hours:.2f} hours)")
        print(f"Computation Time    : {final_cumulative_cost:.6f} Core-Hours / Sim-Second (Cumulative)")
        print("-" * 45)
        
        if not plot_time:
            csv_filename = "simulation_performance.csv"
            file_exists = os.path.isfile(csv_filename)
            try:
                with open(csv_filename, mode='a', newline='') as csv_file:
                    writer = csv.writer(csv_file)
                    if not file_exists:
                        writer.writerow(["Case Name", "Cores", "Last Simulated Time (s)", "Execution Time (s)", "Clock Time (s)", "Computation Time (Core-Hours/Sim-Sec)"])
                    
                    writer.writerow([case_name, num_cores, last_time, last_execution_time, last_clock_time, f"{final_cumulative_cost:.6f}"])
                print(f"Data successfully appended to {csv_filename}")
            except Exception as e:
                print(f"Error writing to CSV: {e}")

        else:
            if len(sim_times) > 0:
                try:
                    import matplotlib.pyplot as plt
                    
                    output_dir = os.path.join(os.getcwd(), "_plots")
                    os.makedirs(output_dir, exist_ok=True)
                    
                    plt.figure(figsize=(12, 6))
                    
                    if plot_type == "diff":
                        plt.plot(sim_times, comp_times, color='#00509E', linewidth=0.8, alpha=0.8, label='Differential')
                        title_prefix = "Step-by-Step"
                    else:
                        plt.plot(sim_times, comp_times, color='#D32F2F', linewidth=1.5, label='Cumulative')
                        title_prefix = "Running Average of"
                        
                    plt.xlabel("Simulated Time (s)", fontweight='bold')
                    plt.ylabel("Computation Time (Core-Hours / Sim-Sec)", fontweight='bold')
                    plt.title(f"{title_prefix} Computation Time: {case_name}", fontweight='bold')
                    plt.grid(True, linestyle='--', alpha=0.5)
                    
                    if abs_limits:
                        plt.ylim(abs_limits[0], abs_limits[1])
                    else:
                        plt.yscale('log') 
                        
                    plt.legend()
                    
                    plot_filename = os.path.join(output_dir, f"{plot_type}_cost_plot_{case_name}.jpg")
                    plt.savefig(plot_filename, format='jpg', dpi=300, bbox_inches='tight')
                    print(f"Plot successfully saved to {plot_filename}")
                    plt.close()
                    
                except ImportError:
                    print("Warning: 'matplotlib' is not installed. Skipping plot generation.")
            else:
                print("Not enough timestep data to generate a plot.")
    else:
        print(f"Could not find required Time or Execution/Clock data in {log_path}.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 simulation_time.py <case_directory> [--time] [--diff | --cumu] [--abs ymin ymax]")
        sys.exit(1)
        
    case_directory = sys.argv[1]
    plot_flag = "--time" in sys.argv
    plot_type = "diff" if "--diff" in sys.argv else "cumu"
    
    abs_limits = None
    if "--abs" in sys.argv:
        try:
            abs_idx = sys.argv.index("--abs")
            ymin = float(sys.argv[abs_idx + 1])
            ymax = float(sys.argv[abs_idx + 2])
            abs_limits = (ymin, ymax)
        except (IndexError, ValueError):
            print("Error: The '--abs' flag requires exactly two numeric arguments (ymin and ymax).")
            print("Example: python3 simulation_time.py case_dir --time --diff --abs 0 40")
            sys.exit(1)
            
    analyze_log(case_directory, plot_flag, plot_type, abs_limits)
